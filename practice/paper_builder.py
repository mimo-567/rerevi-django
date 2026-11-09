"""Resolve topic/style blueprints into actual published practice questions."""
from django.core.exceptions import ValidationError
from .catalogue import COMPONENTS
from .models import Keyword
from .numbering import GROUP_PATTERN,PART_PATTERN
from .selection import choose_slots,previous_wording
from .services import keyword_payload,question_payload
from .worksheets import public_questions,sign_worksheet,text,fingerprint

MARKS={'a':2,'b':5,'c':8,'d':15}

def topic_label(component,number):
    title=next(s[1] for s in COMPONENTS[component]['sections'] if s[0]==number)
    if component=='component-2-christianity':return 'Christian beliefs' if number==1 else 'Christian practices'
    if component=='component-3-islam':return 'Muslim beliefs' if number==1 else 'Muslim practices'
    return title.removeprefix('Issues of ')

def block_catalogue():
    rows=[]
    for component,spec in COMPONENTS.items():
        for number,title,pool in spec['sections']:
            for part in MARKS:
                if part=='a' and component!='component-1-general' and number!=1:continue
                section='all' if part=='a' and component!='component-1-general' else number
                label=spec['name'] if section=='all' else topic_label(component,number)
                rows.append({'component':component,'section':section,'part':part,'theme':label,'subject':spec['name'],'marks':MARKS[part]})
    return rows

def generate_blueprint(data):
    if not isinstance(data,dict):raise ValidationError('Choose a valid paper layout.')
    groups=data.get('groups')
    if not isinstance(groups,list) or not 1<=len(groups)<=60:raise ValidationError('Add a numbered container before building your paper.')
    for flag in ['include_extra','spag']:
        if flag in data and type(data[flag]) is not bool:raise ValidationError('Invalid paper options.')
    questions=public_questions()
    if data.get('include_extra',True) is not True:questions=questions.filter(source_type='official')
    seen_groups=set();seen_numbers=set();slots=[];pools=[]
    for group in groups:
        if not isinstance(group,dict):raise ValidationError('Invalid numbered container.')
        identity=group.get('id');number=group.get('number');title=text(group.get('title'),120).strip()
        if not isinstance(identity,str) or not GROUP_PATTERN.fullmatch(identity) or identity in seen_groups:raise ValidationError('Each container needs a different valid identifier.')
        if type(number) is not int or not 1<=number<=60 or number in seen_numbers:raise ValidationError('Use a different whole question number from 1 to 60 for each container.')
        if not title:raise ValidationError('Give each numbered container a heading.')
        seen_groups.add(identity);seen_numbers.add(number)
        blocks=group.get('slots')
        if not isinstance(blocks,list) or len(blocks)>60:raise ValidationError('Invalid question blocks.')
        labels=set()
        for block in blocks:
            if not isinstance(block,dict):raise ValidationError('Invalid question block.')
            component=block.get('component');part=block.get('part');section=block.get('section');label=block.get('label')
            if not isinstance(component,str) or component not in COMPONENTS or not isinstance(part,str) or part not in MARKS:raise ValidationError('Choose a valid subject and question type for each block.')
            if not isinstance(label,str) or not PART_PATTERN.fullmatch(label) or label in labels:raise ValidationError('Use a different subquestion label, such as a or b(ii), for each block in a container.')
            labels.add(label)
            spec=COMPONENTS[component]
            if section=='all' and part=='a' and component!='component-1-general':source_section=spec['sections'][0]
            else:
                source_section=next((s for s in spec['sections'] if type(section) is int and s[0]==section),None)
                if source_section is None:raise ValidationError('Choose a valid topic for each question block.')
            source_number,source_title,pool=source_section
            if part=='a':choices=list(Keyword.objects.filter(active=True,component=component,pool=pool))
            else:choices=list(questions.filter(component=component,question_number=source_number,part=part))
            if not choices:raise ValidationError(f'No {part.upper()} questions match {topic_label(component,source_number)}. Change the topic or source setting.')
            pools.append(choices);slots.append((part,source_number,source_title,{'group':identity,'number':number,'title':title,'part':label}))
            if len(slots)>60:raise ValidationError('A paper can contain at most 60 question blocks.')
    if not slots:raise ValidationError('Place at least one question block inside a numbered container.')
    items=[]
    for (part,source_number,source_title,layout),chosen in zip(slots,choose_slots(pools,previous_wording(data))):
        row=keyword_payload(chosen,source_number) if part=='a' else question_payload(chosen,spag=data.get('spag') is True)
        if part=='a':row.update(source_type='glossary',collection_id='',section_topic=source_title)
        row['layout']=layout;row['revision']=fingerprint(row);items.append(row)
    components={q['component'] for q in items};component=next(iter(components)) if len(components)==1 else 'mixed'
    return sign_worksheet({'title':text(data.get('title','My practice paper'),200),'component':component,'component_name':COMPONENTS[component]['name'] if component in COMPONENTS else 'Mixed topics','numbering':'exam','instructions':'Answer all questions. The marks for each question are shown.','questions':items})
