import secrets
import json
from functools import lru_cache
from pathlib import Path
import uuid
from django.core import signing
from django.core.exceptions import ValidationError
from .catalogue import COMPONENTS, MARKS, rubric_id, spag_eligible
from .models import Question, Keyword, Rubric
from .answer_space import answer_line_count
from .examiner_reports import report_fields
RNG = secrets.SystemRandom()
STANDARD_D = ['Discuss this statement.', 'Show that you have considered more than one point of view.', 'Refer to religious beliefs and teachings in your answer.']
SPECIAL_D = 'Refer to non-religious beliefs, such as those held by Atheists and Humanists, in your answer.'

def resource_url(path, page=None):
    if not path: return ''
    prefix = 'eduqas_reference/'
    if path.startswith(prefix): path=path[len(prefix):]
    from django.urls import reverse
    url=reverse('resource',kwargs={'relative':path})
    return url+(f'#page={page}' if page else '')

def question_payload(q, spag=False):
    rid=rubric_id(q.component,q.part,q.question_number) if q.part in MARKS else ''
    rubric=Rubric.objects.filter(pk=rid).first()
    rd=rubric.data if rubric else {}
    pdf=rd.get('official_descriptor_pdf') or rd.get('official_descriptor_pdf_by_component',{}).get(q.component,'')
    prompt=q.prompt
    if q.part=='d' and q.source_type=='official':
        statement=prompt.split('Discuss this statement')[0].strip()
        instructions=STANDARD_D+([SPECIAL_D] if q.component=='component-1-general' and q.question_number==2 else [])
        prompt=statement+'\n\n'+'\n'.join(instructions)
    eligible=spag_eligible(q.component,q.part,q.question_number)
    return {**report_fields('re','route-a',q.year,q.series,q.source_type=='official'),'id':q.pk,'kind':'question','component':q.component,'number':q.question_number,'topic':q.topic_name or next(s[1] for s in COMPONENTS[q.component]['sections'] if s[0]==q.question_number),'part':q.part,'answer_lines':answer_line_count(q.part,q.component,q.question_number),'prompt':prompt,'historical_prompt':q.prompt,'marks':q.marks,'spag':6 if spag and eligible else 0,'spag_eligible':eligible,'indicative_content':q.indicative_content.replace('\uf0b7','•'),'scheme_note':('Indicative content is a guide, not an exhaustive checklist. Other valid points may receive credit.' if q.indicative_content.strip() else 'Additional practice — no question-specific mark scheme supplied. General criteria describe answer quality, not the points expected for this question. Self-marking is optional.'),'rubric_url':resource_url(pdf),'spag_rubric_url':resource_url('eduqas_reference/rubrics/spag-official-5.pdf') if spag and eligible else '', 'source_type':q.source_type,'collection_id':str(q.collection_id or ''),'source_reference':q.source_reference,'updated_at':q.updated_at.isoformat(),'section_topic':next(s[1] for s in COMPONENTS[q.component]['sections'] if s[0]==q.question_number),'source_label':('Additional practice · '+str(q.collection)+' · '+q.source_reference).strip(' ·') if q.collection_id else (f'{q.series} {q.year}' if q.year else q.series),'source_url':q.source_url,'original_paper_url':resource_url(q.data.get('source_pdf',''),q.data.get('source_page')),'original_scheme_url':resource_url(q.data.get('mark_scheme_pdf',''),q.data.get('mark_scheme_source_page')) or q.mark_scheme_url}

def keyword_payload(k, number, source_question=None):
    payload = {**report_fields('re','route-a'),'id':str(k.pk),'kind':'keyword','component':k.component,'number':number,'topic':k.term,'part':'a','answer_lines':6,'prompt':f'What is meant by the term “{k.term}”?','marks':2,'spag':0,'spag_eligible':False,'indicative_content':k.definition,'scheme_note':'1 mark: a very simple definition or relevant example. 2 marks: a developed definition, with or without an example. Accept accurate equivalent wording. No creditworthy response: 0.','rubric_url':'','spag_rubric_url':'','source_label':'Official key concepts glossary','source_url':k.source_url,'original_paper_url':'','original_scheme_url':resource_url('eduqas_reference/key-concepts-glossary.pdf',k.source_page)}
    if source_question:
        payload.update({**report_fields('re','route-a',source_question['year'],source_question['series']),'prompt':source_question['prompt'],'past_paper_a':source_question['key'],'source_label':f"{source_question['series']} {source_question['year']}",'source_url':source_question['source_url'],'original_paper_url':resource_url(source_question['source_pdf'],source_question['source_page'])})
    return payload

@lru_cache(maxsize=1)
def past_paper_a():
    return json.loads((Path(__file__).parent/'data'/'past_paper_a.json').read_text())

def parse_int(value, name, low, high):
    try: number=int(value)
    except (ValueError,TypeError): raise ValidationError(f'{name} must be a whole number.')
    if not low<=number<=high: raise ValidationError(f'{name} must be between {low} and {high}.')
    return number

def generate_paper(data):
    component=data.get('component')
    if component not in COMPONENTS: raise ValidationError('Choose a valid component.')
    mode=data.get('mode','keywords')
    if mode not in ('keywords','custom','full'): raise ValidationError('Choose a valid practice mode.')
    spec=COMPONENTS[component]
    section=data.get('section','all')
    sections=spec['sections']
    if section!='all':
        number=parse_int(section,'Section',1,len(sections))
        sections=[s for s in sections if s[0]==number]
    spag=data.get('spag') is True
    items=[]
    year=data.get('year','all')
    from .worksheets import public_questions
    include_extra=data.get('include_extra',True) is True
    pool=public_questions().filter(component=component,part__in=('b','c','d'))
    if not include_extra or year not in ('all','',None): pool=pool.filter(source_type='official')
    if year not in ('all','',None): pool=pool.filter(year=parse_int(year,'Year',2018,2100))
    if mode=='full':
        sections=spec['sections']; chosen_keywords=set()
        for number,title,keypool in sections:
            source_a=None
            if year not in ('all','',None):
                source_a=past_paper_a().get(f'{int(year)}:{component}:{number}')
                if not source_a: raise ValidationError(f'No original Part A question is recorded for {title} in {year}. Choose another year or Any year.')
                k=Keyword.objects.filter(component=component,pool=keypool,active=True,term__iexact=source_a['term']).first()
                if not k: raise ValidationError(f"The original {year} keyword for {title} ({source_a['term']}) is unavailable. Restore it in administration or choose another year.")
            else:
                candidates=list(Keyword.objects.filter(component=component,pool=keypool,active=True).exclude(pk__in=chosen_keywords))
                if not candidates: raise ValidationError(f'No keywords available for {title}. Add one in administration.')
                k=RNG.choice(candidates)
            chosen_keywords.add(k.pk);items.append(keyword_payload(k,number,source_a))
            for part in ('b','c','d'):
                candidates=list(pool.filter(question_number=number,part=part))
                if not candidates: raise ValidationError(f'No {part.upper()} question is available for {title} with this year filter.')
                items.append(question_payload(RNG.choice(candidates),spag))
        title=spec['label']+' · Full practice paper';minutes=spec['minutes']
    elif mode=='keywords':
        pools={s[2] for s in sections}
        candidates=list(Keyword.objects.filter(component=component,pool__in=pools,active=True))
        count=parse_int(data.get('count',8),'Number of keywords',1,51)
        if count>len(candidates): raise ValidationError(f'This selection has {len(candidates)} different keywords. Choose that many or fewer.')
        items=[keyword_payload(k,i+1) for i,k in enumerate(RNG.sample(candidates,count))]
        title=spec['label']+' · Keyword practice';minutes=None;spag=False
    else:
        parts=data.get('parts',['b','c','d'])
        if not isinstance(parts,list) or not parts or any(p not in MARKS for p in parts): raise ValidationError('Select at least one of B, C or D.')
        candidates=list(pool.filter(question_number__in=[s[0] for s in sections],part__in=parts))
        count=parse_int(data.get('count',6),'Number of questions',1,30)
        if count>len(candidates): raise ValidationError(f'Only {len(candidates)} matching questions are available. Reduce the count or widen your filters.')
        items=[question_payload(q,spag) for q in RNG.sample(candidates,count)]
        title=spec['label']+' · Focused practice';minutes=None
    paper={'id':uuid.uuid4().hex,'title':title,'component':component,'component_name':spec['name'],'mode':mode,'minutes':minutes,'spag_enabled':spag,'questions':items,'total_marks':sum(x['marks']+x['spag'] for x in items)}
    snapshot={'id':paper['id'],'component':component,'mode':mode,'title':title,'minutes':minutes,'spag':spag,'items':[{'kind':i['kind'],'id':i['id'],'number':i['number'],**({'past_paper_a':i['past_paper_a']} if 'past_paper_a' in i else {})} for i in items]}
    paper['token']=signing.dumps(snapshot,salt='practice-paper',compress=True)
    return paper

def paper_from_token(token):
    try: snapshot=signing.loads(token,salt='practice-paper',max_age=60*60*24*30)
    except signing.BadSignature: raise ValidationError('This download has expired. Generate a new paper; your browser answers are still available to export.')
    if 'portable' in snapshot:
        from .worksheets import validate_paper
        return validate_paper(snapshot['portable'])
    items=[]
    for item in snapshot['items']:
        if item['kind']=='keyword':
            k=Keyword.objects.filter(pk=item['id'],active=True).first()
            if not k: raise ValidationError('A keyword in this paper is no longer available. Generate a new paper.')
            source_a=past_paper_a().get(item['past_paper_a']) if item.get('past_paper_a') else None
            if item.get('past_paper_a') and not source_a: raise ValidationError('The original Part A reference is no longer available. Generate a new paper.')
            items.append(keyword_payload(k,item['number'],source_a))
        else:
            q=Question.objects.filter(pk=item['id'],active=True).first()
            if not q: raise ValidationError('A question in this paper is no longer available. Generate a new paper.')
            items.append(question_payload(q,snapshot['spag']))
    return {**snapshot,'questions':items,'total_marks':sum(i['marks']+i['spag'] for i in items),'component_name':COMPONENTS[snapshot['component']]['name']}
