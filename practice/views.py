import csv
import io
import json
import uuid
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_safe, require_POST, require_http_methods
from .catalogue import COMPONENTS
from .models import Question, Keyword, ImportLog
from .services import generate_paper, paper_from_token

@require_safe
def home(request):
    from .examiner_reports import reports
    catalogue=[]
    for key,spec in COMPONENTS.items():
        catalogue.append({'id':key,**spec,'years':list(Question.objects.filter(component=key,active=True,year__isnull=False).order_by('-year').values_list('year',flat=True).distinct()),'question_count':Question.objects.filter(component=key,active=True).count(),'keyword_count':Keyword.objects.filter(component=key,active=True).count()})
    return render(request,'practice/home.html',{'examiner_reports':[r for r in reports() if r['subject']=='re'],'catalogue':catalogue,'question_count':Question.objects.filter(active=True).count(),'keyword_count':Keyword.objects.filter(active=True).count()})

@require_POST
def generate(request):
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict): raise ValidationError('Invalid paper options.')
        paper=generate_paper(data)
    except (ValueError,ValidationError) as error:
        return JsonResponse({'error':' '.join(error.messages) if isinstance(error,ValidationError) else 'Invalid request.'},status=400)
    return JsonResponse(paper)

@require_POST
def pdf(request):
    try:
        token=request.POST.get('token','')
        if len(token)>20000: raise ValidationError('Invalid paper token.')
        paper=paper_from_token(token)
        from .pdf import make_pdf
        options={'theme':request.POST.get('theme','classic'),'cover':request.POST.get('cover','1' if paper['mode']=='full' else '0')=='1','back_pages':request.POST.get('back_pages','0')}
        response=HttpResponse(make_pdf(paper,options),content_type='application/pdf')
        disposition='inline' if request.POST.get('presentation')=='print' else 'attachment'
        response['Content-Disposition']=disposition+'; filename="rerevi-practice-paper.pdf"'
        return response
    except ValidationError as error:
        return render(request,'practice/error.html',{'message':' '.join(error.messages)},status=400)

@require_safe
@xframe_options_sameorigin
def resource(request,relative):
    root=settings.RESOURCE_ROOT
    target=(root/relative).resolve()
    if not target.is_relative_to(root) or target.suffix.lower()!='.pdf' or not target.is_file(): raise Http404
    return FileResponse(target.open('rb'),content_type='application/pdf',filename=target.name)

@require_safe
def health(request):
    with connection.cursor() as cursor: cursor.execute('SELECT 1')
    return JsonResponse({'status':'ok'})

@require_http_methods(['GET','POST'])
def access(request):
    error=''
    if settings.PUBLIC_ACCESS: return redirect('home')
    if request.method=='POST':
        key='private-login:'+request.META.get('REMOTE_ADDR','unknown')
        attempts=cache.get(key,0)
        if attempts>=10: error='Too many attempts. Try again in 15 minutes.'
        elif settings.PRIVATE_ACCESS_HASH and check_password(request.POST.get('code',''),settings.PRIVATE_ACCESS_HASH):
            request.session.cycle_key();request.session['practice_access']=True
            return redirect('home')
        else:
            cache.set(key,attempts+1,900);error='That access code was not recognised.'
    return render(request,'practice/access.html',{'error':error})

@require_safe
def privacy(request): return render(request,'practice/privacy.html')

CSV_FIELDS=['component','question_number','part','prompt','indicative_content','year','series','source_url','mark_scheme_url','collection_id','source_reference','topic_name']

@staff_member_required
@require_http_methods(['GET','POST'])
def import_questions(request):
    import re
    import difflib
    from .models import ResourceCollection
    if not request.user.has_perm('practice.add_question'):
        return HttpResponse('You do not have permission to add questions.',status=403)
    errors=[];warnings=[];candidates=[]
    collections=ResourceCollection.objects.all()
    if request.method=='POST':
        uploaded=request.FILES.get('file')
        if not uploaded: errors.append('Choose a CSV file.')
        elif uploaded.size>1024*1024: errors.append('The CSV must be smaller than 1 MB.')
        else:
            try:
                reader=csv.DictReader(io.StringIO(uploaded.read().decode('utf-8-sig')))
                if not reader.fieldnames or 'prompt' not in reader.fieldnames: raise ValueError('The CSV needs a prompt column. Other classification columns may be left blank for drafts.')
                normal=lambda value:re.sub(r'\W+','',value.casefold())
                existing={normal(prompt):identifier for identifier,prompt in Question.objects.values_list('id','prompt')}
                seen=set()
                collection_map={str(c.pk):c for c in collections}
                for line,row in enumerate(reader,2):
                    if line>501: raise ValueError('Import at most 500 questions at once.')
                    try:
                        prompt=row.get('prompt','').strip();fingerprint=normal(prompt)
                        if fingerprint in existing or fingerprint in seen: raise ValueError('Identical question already exists in the bank or this file.')
                        collection_id=(row.get('collection_id') or request.POST.get('collection') or '').strip()
                        if collection_id and collection_id not in collection_map: raise ValueError('Unknown resource collection.')
                        obj=Question(id='custom-'+uuid.uuid4().hex,component=row.get('component','').strip(),question_number=int(row['question_number']) if row.get('question_number','').strip() else None,part=row.get('part','').strip().lower(),prompt=prompt,indicative_content=row.get('indicative_content','').strip(),year=int(row['year']) if row.get('year','').strip() else None,series=row.get('series','').strip() or 'Admin added',source_url=row.get('source_url','').strip(),mark_scheme_url=row.get('mark_scheme_url','').strip(),source_type='additional',status='draft',collection=collection_map.get(collection_id),source_reference=row.get('source_reference','').strip(),topic_name=(row.get('topic_name') or row.get('topic') or '').strip())
                        obj.full_clean();candidates.append(obj);seen.add(fingerprint)
                        similar=difflib.get_close_matches(fingerprint,existing.keys(),n=1,cutoff=.88)
                        if similar: warnings.append(f'Row {line}: similar to {existing[similar[0]]}. Review the wording before publishing.')
                    except (ValueError,ValidationError) as error:
                        errors.append(f'Row {line}: '+('; '.join(error.messages) if isinstance(error,ValidationError) else str(error)))
                        if len(errors)>=20: break
                if not candidates and not errors: errors.append('The file has no questions.')
                if not errors and request.POST.get('confirm')=='yes':
                    with transaction.atomic():
                        Question.objects.bulk_create(candidates)
                        ImportLog.objects.create(actor=request.user.get_username(),count=len(candidates),filename=Path(uploaded.name).name[:200])
                    messages.success(request,f'Added {len(candidates)} draft questions. Classify and review them before publishing.')
                    return redirect('admin:practice_question_changelist')
            except (ValueError,UnicodeError,csv.Error) as error: errors.append(str(error))
    return render(request,'practice/import.html',{'errors':errors,'warnings':warnings,'preview':candidates,'collections':collections,'chosen_collection':request.POST.get('collection','')})

@staff_member_required
@require_safe
def csv_template(request):
    response=HttpResponse(content_type='text/csv');response['Content-Disposition']='attachment; filename="rerevi-question-template.csv"'
    writer=csv.writer(response);writer.writerow(CSV_FIELDS)
    writer.writerow(['component-2-christianity',1,'b','Describe Christian beliefs about the Trinity.','Marking guidance: describe God as Father, Son and Holy Spirit; one God in three persons. Other valid points may be credited.','','Admin added','','','','Worksheet 1, Q1','Trinity'])
    return response

@require_POST
def share_create(request):
    from .sharing import create_share, delete_share, SharingFull
    if len(request.body)>800000: return JsonResponse({'error':'This submission is too large. Download your answers instead.'},status=413)
    try:
        options=json.loads(request.body)
        if not isinstance(options,dict): raise ValidationError('Invalid sharing options.')
        result=create_share(options)
        previous=options.get('previous_share')
        if isinstance(previous,dict):
            result['previous_deleted']=delete_share(previous.get('token'),previous.get('delete_token'))
        return JsonResponse(result,status=201)
    except SharingFull:
        return JsonResponse({'error':'Answer sharing is temporarily full. Please download your answers and email them instead.'},status=503)
    except (ValueError,ValidationError) as error:
        return JsonResponse({'error':' '.join(error.messages) if isinstance(error,ValidationError) else 'Invalid request.'},status=400)

@require_POST
def share_delete(request):
    from .sharing import delete_share
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict): raise ValueError
        deleted=delete_share(data.get('token'),data.get('delete_token'))
    except (ValueError,TypeError): return JsonResponse({'error':'Invalid deletion request.'},status=400)
    if not deleted: return JsonResponse({'error':'This link has already expired, was deleted, or the deletion key is invalid.'},status=404)
    return JsonResponse({'deleted':True})

@require_safe
def shared_answers(request,token):
    from datetime import datetime
    from .sharing import load_share
    data=load_share(token)
    if data is None:
        return render(request,'practice/share_missing.html',status=404)
    if data.get('subject','re')!='re':return render(request,'practice/share_missing.html',status=404)
    data={k:v for k,v in data.items() if k!='delete_hash'}
    data['created_at']=datetime.fromisoformat(data['created_at'])
    data['expires_at']=datetime.fromisoformat(data['expires_at'])
    return render(request,'practice/shared.html',{'snapshot':data})


@require_safe
def manage_submission(request):
    return render(request,'practice/manage_submission.html')

@require_http_methods(['GET','POST'])
def feedback(request):
    from django.utils.crypto import salted_hmac
    from .forms import FeedbackForm
    initial={}
    question=None
    question_id=request.POST.get('question_id') if request.method=='POST' else request.GET.get('question')
    if question_id:
        from .worksheets import public_questions
        question=public_questions().filter(pk=str(question_id)[:150]).first()
        if question:
            initial={'category':'content','subject':f'Question correction: {question.pk}'[:150]}
    form = FeedbackForm(request.POST or None,initial=initial)
    if request.method == 'POST' and form.is_valid():
        if form.cleaned_data.get('website'):
            return redirect('feedback_thanks')
        # Store a keyed hash for rate limiting, not the address in the feedback.
        address = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR','unknown')
        key = 'feedback-rate-'+salted_hmac('feedback-limit',address).hexdigest()
        count = cache.get(key,0)
        if count >= 5:
            form.add_error(None,'Too many feedback messages. Please try again in an hour, or email rerevi@zafirshirazi.com.')
        else:
            with transaction.atomic():
                report=form.save(commit=False)
                if question:
                    report.question=question
                    report.question_reference=f'{question.component} · {question.year or question.series} · {question.question_number}({question.part}) · {question.pk}'[:300]
                report.save()
                from .models import AdminNotification
                AdminNotification.objects.create(feedback=report)
            cache.set(key,count+1,3600)
            if report.email_updates:
                from .email_jobs import feedback_email
                try:feedback_email(report,'feedback_received',address)
                except Exception:messages.warning(request,'Your feedback was saved, but the acknowledgement could not be queued. You can still contact support for updates.')
            return redirect('feedback_thanks')
    return render(request,'practice/feedback.html',{'form':form,'reported_question':question})

@require_safe
def feedback_thanks(request):
    return render(request,'practice/feedback_thanks.html')

@require_safe
def help_page(request):
    from .models import FAQ
    from .content import clean_content
    from django.db.models import Q
    from django.utils.safestring import mark_safe
    search=request.GET.get('q','').strip()[:100]
    rows=FAQ.objects.filter(published=True,site='re')
    if search:rows=rows.filter(Q(question__icontains=search)|Q(answer__icontains=search))
    order={'Getting started':0,'Questions and marking':1,'Saving and practice files':2,'Printing and worksheets':3,'Sharing and privacy':4,'Troubleshooting and feedback':5}
    faqs=[{'id':row.pk,'question':row.question,'answer':mark_safe(clean_content(row.answer)),'category':row.category,'position':row.position} for row in rows]
    faqs.sort(key=lambda row:(order.get(row['category'],99),row['category'].casefold(),row['position'],row['question'].casefold()))
    return render(request,'practice/help.html',{'faqs':faqs,'search':search})

@require_safe
def worksheets(request):
    return render(request,'practice/worksheets.html',{'import_requested':request.GET.get('import')=='1'})

@require_safe
def worksheet_catalogue(request):
    from .worksheets import catalogue_rows
    from .models import ResourceCollection
    return JsonResponse({'questions':catalogue_rows(),'collections':list(ResourceCollection.objects.filter(published=True,permission_status='allowed').values('id','title','kind','chapter'))})

@require_POST
def worksheet_prepare(request):
    from .worksheets import sign_worksheet
    try:
        if len(request.body)>1800000: raise ValidationError('Worksheet is too large.')
        return JsonResponse(sign_worksheet(json.loads(request.body)))
    except (ValueError,TypeError,ValidationError) as error:
        return JsonResponse({'error':' '.join(error.messages) if isinstance(error,ValidationError) else 'Invalid worksheet.'},status=400)

@require_POST
def worksheet_pdf(request):
    from .worksheets import validate_paper
    from .worksheet_pdf import make_worksheet_pdf
    try:
        data=json.loads(request.POST.get('worksheet','{}'))
        paper=validate_paper(data.get('paper'))
        content=make_worksheet_pdf(paper,data.get('options',{}),data.get('document','questions'))
        response=HttpResponse(content,content_type='application/pdf')
        response['Content-Disposition']='attachment; filename="rerevi-'+paper['reference']+'.pdf"'
        return response
    except (ValueError,TypeError,ValidationError) as error:
        return render(request,'practice/error.html',{'message':' '.join(error.messages) if isinstance(error,ValidationError) else 'Invalid worksheet PDF options.'},status=400)

@require_safe
def updates(request):
    from .models import UpdatePost
    from .content import clean_content
    from django.utils.safestring import mark_safe
    posts=[{'title':p.title,'body':mark_safe(clean_content(p.body)),'kind':p.kind,'resolved':p.resolved,'date':p.created_at} for p in UpdatePost.objects.filter(published=True,site='re')]
    return render(request,'practice/updates.html',{'posts':posts})

@require_safe
def articles(request):
    from .models import Article
    return render(request,'practice/articles.html',{'articles':Article.visible().filter(site='re')})

@require_safe
def article_detail(request,slug):
    from .models import Article
    from .content import render_article
    from django.shortcuts import get_object_or_404
    from django.utils.safestring import mark_safe
    preview=request.GET.get('preview')=='1' and request.user.has_perm('practice.view_article')
    queryset=(Article.objects.all() if preview else Article.visible()).filter(site='re')
    article=get_object_or_404(queryset,slug=slug)
    response=render(request,'practice/article.html',{'article':article,'article_body':mark_safe(render_article(article)),'article_preview':preview})
    if preview:response['X-Robots-Tag']='noindex, nofollow, noarchive'
    return response


@require_POST
def email_share_receipt(request):
    import hashlib,hmac
    from .sharing import load_share,TOKEN_RE
    from .email_jobs import queue_email
    try:
        if len(request.body)>5000:raise ValidationError('Invalid receipt request.')
        options=json.loads(request.body)
        if not isinstance(options,dict):raise ValueError
        token=options.get('token');deletion=options.get('delete_token')
        if not isinstance(deletion,str) or not TOKEN_RE.fullmatch(deletion):raise ValidationError('The private deletion key is invalid.')
        snapshot=load_share(token)
        if snapshot is None or not hmac.compare_digest(hashlib.sha256(deletion.encode()).hexdigest(),snapshot.get('delete_hash','')):
            return JsonResponse({'error':'This submission is unavailable or the private deletion key is invalid.'},status=404)
        brand='RE Revi'
        base=settings.PUBLIC_BASE_URL
        url=base+'/s/'+token+'/'
        private=base+'/s/manage/#'+token+'.'+deletion
        body=f"""A private submission receipt was requested on {brand} for this email address.

Submitted: {snapshot["created_at"]}
Expires: {snapshot["expires_at"]}

Viewing link (share this with your teacher):
{url}

PRIVATE deletion link (keep this for yourself):
{private}

Anyone with the private link can permanently delete this submission. Open it and confirm deletion. Do not forward the private link to your teacher.

The server snapshot is deleted within 30 days of creation; copies people save themselves are outside that process. No answers are included in this email.
If this email was unexpected, you can ignore it. Contact rerevi@zafirshirazi.com for help."""
        address=request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR','unknown')
        queue_email('share_receipt',options.get('email'),body,address=address,share_token=token)
        return JsonResponse({'queued':True,'message':'Receipt queued. Delivery is normally attempted within a minute. Check your inbox and spam folder; save a downloaded copy too.'},status=202)
    except (ValueError,TypeError,ValidationError) as error:
        return JsonResponse({'error':' '.join(error.messages) if isinstance(error,ValidationError) else 'Invalid receipt request.'},status=400)
    except OSError:
        return JsonResponse({'error':'Email is temporarily unavailable. Save your private receipt as a file instead.'},status=503)
