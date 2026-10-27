"""Owner-only submission moderation; never send answers or access keys to admin."""
import json
import re
from datetime import datetime
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

FILE_ID = re.compile(r'^[a-f0-9]{64}$')

def metadata(path):
    if path.is_symlink(): return None
    try:
        snapshot = json.loads(path.read_text())
        expires = datetime.fromisoformat(snapshot['expires_at'])
        if timezone.is_naive(expires) or expires <= timezone.now():
            path.unlink(missing_ok=True)
            return None
        submitted = datetime.fromisoformat(snapshot['created_at'])
        if timezone.is_naive(submitted): return None
        # Only these fields may leave this function. Never return the snapshot.
        return {'id':path.stem,'name':str(snapshot.get('name') or 'Anonymous')[:100],'submitted':submitted}
    except (FileNotFoundError,ValueError,KeyError,TypeError): return None

@require_http_methods(['GET','POST'])
def submissions(request):
    if not request.user.is_superuser: raise PermissionDenied
    context = {**admin.site.each_context(request),'title':'Shared submissions'}
    if request.method == 'POST':
        identifier = request.POST.get('submission','')
        if not FILE_ID.fullmatch(identifier): raise PermissionDenied
        path = settings.SHARE_DIR / (identifier+'.json')
        row = metadata(path)
        if row is None:
            messages.info(request,'This submission has already expired or been deleted.')
            return redirect('admin_submissions')
        if request.POST.get('confirm') != 'yes':
            return render(request,'admin/submission_confirm.html',{**context,'submission':row})
        path.unlink(missing_ok=True)
        messages.success(request,'The shared submission was permanently deleted.')
        return redirect('admin_submissions')
    search = request.GET.get('q','').strip()[:100]
    rows = []
    for path in settings.SHARE_DIR.glob('*.json'):
        if not FILE_ID.fullmatch(path.stem): continue
        row = metadata(path)
        if row and (not search or search.casefold() in row['name'].casefold()): rows.append(row)
    rows.sort(key=lambda row:row['submitted'],reverse=True)
    context.update({'page':Paginator(rows,50).get_page(request.GET.get('page')),'search':search})
    return render(request,'admin/submissions.html',context)

@require_http_methods(['GET','POST'])
def email_settings(request):
    from django import forms
    from .notifications import mail_config,save_mail_config,connection
    from django.core.mail import EmailMessage
    if not request.user.is_superuser: raise PermissionDenied
    class MailForm(forms.Form):
        enabled=forms.BooleanField(required=False,label='Enable owner report emails')
        password=forms.CharField(required=False,max_length=500,strip=False,widget=forms.PasswordInput(render_value=False),label='SMTP password',help_text='Leave blank to keep the saved password. Use the SMTP password supplied by your mail provider.')
    from .email_jobs import outbox_counts
    config=mail_config()
    form=MailForm(request.POST or None,initial={'enabled':config.get('enabled',False)})
    if request.method=='POST' and form.is_valid():
        try:
            save_mail_config(form.cleaned_data['enabled'],form.cleaned_data['password'])
            if request.POST.get('action')=='test':
                conn=connection()
                if conn is None: raise ValueError('Enable notifications and save an alias password first.')
                EmailMessage('RE Revi notification setup','Your RE Revi report notifications are configured.\n\nOpen your admin inbox: '+settings.PUBLIC_BASE_URL+'/admin/practice/adminnotification/','RE Revi <'+settings.SMTP_FROM+'>',[settings.SMTP_OWNER],connection=conn).send(fail_silently=False)
                messages.success(request,'Settings saved. SMTP accepted the setup email to the configured owner address; check your inbox and spam folder.')
            else: messages.success(request,'Notification settings saved. The worker checks pending reports every minute.')
            return redirect('admin_email_settings')
        except ValueError as error: form.add_error(None,str(error))
        except Exception: form.add_error(None,'Settings saved, but SMTP delivery failed. Check your alias password and outbound SMTP setup in Forward Email.')
    return render(request,'admin/email_settings.html',{**admin.site.each_context(request),'title':'Owner email notifications','smtp_host':settings.SMTP_HOST,'smtp_port':settings.SMTP_PORT,'smtp_owner':settings.SMTP_OWNER,'smtp_username':settings.SMTP_USERNAME,'form':form,'password_saved':bool(config.get('password')),'outbox':outbox_counts()})

@require_http_methods(['GET','POST'])
def restore_content(request,revision_id):
    from .models import ContentRevision
    from django.shortcuts import get_object_or_404
    if not request.user.has_perm('practice.change_sitecontent'): raise PermissionDenied
    revision=get_object_or_404(ContentRevision,pk=revision_id)
    if request.method=='POST':
        revision.content.body=revision.body;revision.content.save()
        messages.success(request,'Website content restored. The replaced version was saved to history.')
        return redirect('admin:practice_sitecontent_change',revision.content_id)
    from .content import clean_content
    from django.utils.safestring import mark_safe
    return render(request,'admin/restore_content.html',{**admin.site.each_context(request),'title':'Restore website text','revision':revision,'preview':mark_safe(clean_content(revision.body))})

@require_http_methods(['GET'])
def preview(request,kind,object_id):
    from .models import Question,SiteContent,Announcement
    from django.shortcuts import get_object_or_404
    from .content import clean_content
    from django.utils.safestring import mark_safe
    model={'question':Question,'content':SiteContent,'announcement':Announcement}.get(kind)
    if model is None: raise PermissionDenied
    if not request.user.has_perm('practice.view_'+model._meta.model_name): raise PermissionDenied
    obj=get_object_or_404(model,pk=object_id)
    context={'preview_title':str(obj),'is_question':kind=='question'}
    if kind=='question': context.update({'preview_prompt':obj.prompt,'preview_guidance':obj.indicative_content or 'No question-specific mark scheme supplied.','preview_source':str(obj.collection or obj.series),'preview_marks':obj.marks})
    else: context['preview_body']=mark_safe(clean_content(obj.body))
    return render(request,'practice/admin_preview.html',context)

@require_http_methods(['GET','POST'])
def bulk_questions(request):
    from django import forms
    from django.core import signing
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from .catalogue import COMPONENT_CHOICES
    from .models import Question,ResourceCollection,QuestionRevision
    if not request.user.has_perm('practice.change_question'): raise PermissionDenied
    token=request.POST.get('selection') or request.GET.get('selection','')
    try:
        selection=signing.loads(token,salt='bulk-questions',max_age=1800)
        if selection['user']!=request.user.pk or len(selection['ids'])>500: raise ValueError
    except (signing.BadSignature,ValueError,KeyError,TypeError): raise PermissionDenied
    class BulkForm(forms.Form):
        component=forms.ChoiceField(required=False,choices=[('','Keep current')]+COMPONENT_CHOICES)
        question_number=forms.ChoiceField(required=False,choices=[('','Keep current')]+[(str(i),str(i)) for i in range(1,5)])
        part=forms.ChoiceField(required=False,choices=[('','Keep current')]+[(v,v.upper()) for v in 'abcd'])
        topic_name=forms.CharField(required=False,max_length=200)
        collection=forms.ModelChoiceField(required=False,queryset=ResourceCollection.objects.all(),empty_label='Keep current')
        source_reference=forms.CharField(required=False,max_length=200)
        status=forms.ChoiceField(required=False,choices=[('','Keep current'),('draft','Draft'),('review','Awaiting review'),('published','Published')])
        reason=forms.CharField(required=True,max_length=500)
    form=BulkForm(request.POST or None)
    questions=list(Question.objects.filter(pk__in=selection['ids']))
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                revisions=[]
                for q in questions:
                    previous={k:getattr(q,k) for k in ('component','question_number','part','topic_name','source_reference','status')}
                    previous['collection_id']=q.collection_id
                    for field in ('component','question_number','part','topic_name','collection','source_reference','status'):
                        value=form.cleaned_data.get(field)
                        if value:
                            if field=='question_number': value=int(value)
                            setattr(q,field,value)
                    if form.cleaned_data.get('collection'): q.source_type='additional'
                    q.full_clean();revisions.append(QuestionRevision(question=q,previous=previous,reason=form.cleaned_data['reason']))
                for q in questions:q.save()
                QuestionRevision.objects.bulk_create(revisions)
            messages.success(request,f'{len(questions)} questions updated.')
            return redirect('admin:practice_question_changelist')
        except ValidationError as error: form.add_error(None,'; '.join(error.messages))
    return render(request,'admin/bulk_questions.html',{**admin.site.each_context(request),'title':'Bulk edit questions','form':form,'selection':token,'questions':questions})
