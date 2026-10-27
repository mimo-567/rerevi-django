"""Public worksheet catalogue and validated, portable practice snapshots."""
import hashlib
import json
import uuid
from django.core import signing
from django.core.exceptions import ValidationError
from django.db.models import Q
from .catalogue import COMPONENTS
from .content import safe_link
from .models import Question, Keyword
from .services import question_payload, keyword_payload

PAPER_MARKS={'a':2,'b':5,'c':8,'d':15}

def public_questions():
    return Question.objects.filter(active=True,status='published').filter(Q(source_type='official')|Q(source_type='additional',collection__published=True,collection__permission_status='allowed')).select_related('collection')

def fingerprint(q):
    return hashlib.sha256(json.dumps({k:q.get(k) for k in ('prompt','indicative_content','marks','source_label')},sort_keys=True).encode()).hexdigest()

def catalogue_rows():
    rows=[]
    for q in public_questions():
        row=question_payload(q);row['revision']=fingerprint(row);rows.append(row)
    for k in Keyword.objects.filter(active=True):
        number=next(s[0] for s in COMPONENTS[k.component]['sections'] if s[2]==k.pool)
        row=keyword_payload(k,number);row['source_type']='glossary';row['collection_id']='';row['section_topic']=next(s[1] for s in COMPONENTS[k.component]['sections'] if s[0]==number);row['revision']=fingerprint(row);rows.append(row)
    return rows

def text(value,maximum,default=''):
    if value is None: return default
    if not isinstance(value,str) or len(value)>maximum: raise ValidationError('Invalid or oversized worksheet text.')
    return value

def validate_paper(raw):
    if not isinstance(raw,dict): raise ValidationError('Choose a valid worksheet file.')
    questions=raw.get('questions')
    if not isinstance(questions,list) or not 1<=len(questions)<=60: raise ValidationError('A worksheet must contain 1–60 questions.')
    result=[]; seen=set()
    for index,q in enumerate(questions):
        if not isinstance(q,dict) or q.get('part') not in PAPER_MARKS: raise ValidationError('Every question must have a valid A/B/C/D style.')
        item={k:text(q.get(k,''),limit) for k,limit in {'id':150,'kind':20,'component':50,'topic':200,'section_topic':200,'prompt':10000,'indicative_content':50000,'scheme_note':2000,'source_label':400,'source_type':30,'source_reference':200,'revision':100,'historical_prompt':10000,'examiner_report_title':400,'examiner_report_note':1000}.items()}
        if not item['prompt'].strip(): raise ValidationError('A question has no text.')
        if item['kind'] not in ('question','keyword'): raise ValidationError('Invalid question type.')
        identity=(item['kind'],item['id'])
        if identity in seen: raise ValidationError('A worksheet cannot repeat the same question identifier.')
        seen.add(identity)
        item['part']=q['part'];item['marks']=PAPER_MARKS[q['part']]
        item['number']=int(q.get('number',index+1)) if type(q.get('number',index+1)) is int else index+1
        if not 1<=item['number']<=60: item['number']=index+1
        item['spag']=6 if q.get('spag')==6 and item['component'] in ('component-1-general','component-2-christianity') and item['number']==1 and item['part']=='d' else 0
        for field in ('source_url','original_paper_url','original_scheme_url','rubric_url','spag_rubric_url','examiner_report_url'):
            value=text(q.get(field,''),2000)
            try: item[field]=safe_link(value)
            except ValueError: item[field]=''
        item['collection_id']=str(q.get('collection_id',''))[:30]
        if q.get('past_paper_a'): item['past_paper_a']=text(q['past_paper_a'],150)
        result.append(item)
    paper={'id':text(raw.get('id',uuid.uuid4().hex),100),'title':text(raw.get('title','My practice worksheet'),200),'component':text(raw.get('component','mixed'),50),'component_name':text(raw.get('component_name','Mixed topics'),200),'mode':'worksheet','minutes':None,'spag':any(q['spag'] for q in result),'questions':result,'instructions':text(raw.get('instructions','Answer the selected questions.'),3000),'reference':text(raw.get('reference',''),50)}
    paper['total_marks']=sum(q['marks']+q['spag'] for q in result)
    paper['reference']=paper['reference'] or hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:10].upper()
    return paper

def sign_worksheet(raw):
    paper=validate_paper(raw)
    paper['token']=signing.dumps({'portable':paper},salt='practice-paper',compress=True)
    return paper
