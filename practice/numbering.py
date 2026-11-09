"""Display numbering is independent of source question numbers and marking rules."""
import re
from django.core.exceptions import ValidationError

PART_PATTERN=re.compile(r'[a-z](?:\([ivxlcdm]{1,8}\))?\Z')
GROUP_PATTERN=re.compile(r'[A-Za-z0-9:_-]{1,100}\Z')

def validate_layout(value):
    if not isinstance(value,dict):raise ValidationError('Invalid question-tree entry.')
    group=value.get('group');number=value.get('number');title=value.get('title');part=value.get('part')
    if not isinstance(group,str) or not GROUP_PATTERN.fullmatch(group):raise ValidationError('Invalid question-tree group.')
    if type(number) is not int or not 1<=number<=60:raise ValidationError('Main question numbers must be whole numbers from 1 to 60.')
    if not isinstance(title,str) or not title.strip() or len(title)>120:raise ValidationError('Give each main question a heading of up to 120 characters.')
    if not isinstance(part,str) or not PART_PATTERN.fullmatch(part):raise ValidationError('Use subquestion labels such as a, b or b(ii).')
    return {'group':group,'number':number,'title':title.strip(),'part':part}

def validate_tree(questions):
    groups={};numbers={};labels=set();closed=set();previous=None
    for q in questions:
        layout=validate_layout(q.get('layout'))
        q['layout']=layout
        group=layout['group'];header=(layout['number'],layout['title'])
        if group in groups and groups[group]!=header:raise ValidationError('Questions in one group must share the same number and heading.')
        if layout['number'] in numbers and numbers[layout['number']]!=group:raise ValidationError('Each main question needs a different display number.')
        if previous is not None and previous!=group:closed.add(previous)
        if group in closed:raise ValidationError('Keep each main question\'s subquestions together.')
        label=(group,layout['part'])
        if label in labels:raise ValidationError('Each subquestion label must be unique within its main question.')
        groups[group]=header;numbers[layout['number']]=group;labels.add(label);previous=group

def question_label(paper,q,index,include_group=False):
    if paper.get('numbering')=='exam':
        layout=q['layout'];part=layout['part'];label='('+part[0]+')'+part[1:]
        return str(layout['number'])+label if include_group else label
    return f"{index+1} ({q['part']})"

def group_heading(q):
    return f"{q['layout']['number']}. {q['layout']['title']}"
