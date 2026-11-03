"""Random choices that exhaust distinct question wording before repeating it."""
import re
import secrets
import unicodedata
from django.core.exceptions import ValidationError

RNG=secrets.SystemRandom()

def wording_key(item):
    if isinstance(item,dict):
        part=item.get('part','a')
        prompt=item.get('topic','') if item.get('kind')=='keyword' else item.get('prompt','')
    else:
        part='a' if hasattr(item,'term') else item.part
        prompt=item.term if hasattr(item,'term') else item.prompt
    if part=='d':prompt=re.split('discuss this statement',prompt,maxsplit=1,flags=re.I)[0]
    prompt=unicodedata.normalize('NFKC',prompt).casefold()
    return part+':'+re.sub(r'[^\w]+',' ',prompt).strip()

def record_key(item):
    if isinstance(item,dict):return (item['kind'],str(item['id']))
    return ('keyword' if hasattr(item,'term') else 'question',str(item.pk))

def previous_wording(data):
    """Resolve only public IDs; clients do not send answers or store server history."""
    raw=data.get('avoid',[])
    if not isinstance(raw,list) or len(raw)>60:raise ValidationError('Invalid previous-question selection.')
    ids={'question':[],'keyword':[]}
    for row in raw:
        if not isinstance(row,dict) or not isinstance(row.get('kind'),str) or row['kind'] not in ids:raise ValidationError('Invalid previous-question reference.')
        identifier=row.get('id')
        if not isinstance(identifier,str) or not 1<=len(identifier)<=150:raise ValidationError('Invalid previous-question reference.')
        if row['kind']=='keyword' and (not identifier.isascii() or not identifier.isdigit() or len(identifier)>18):raise ValidationError('Invalid keyword reference.')
        ids[row['kind']].append(identifier)
    from .models import Keyword
    from .worksheets import public_questions
    return {wording_key(q) for q in public_questions().filter(pk__in=ids['question'])}|{wording_key(k) for k in Keyword.objects.filter(active=True,pk__in=ids['keyword'])}

def choose_slots(pools,avoid=()):
    """Match slots to unique wording, then reuse wording only for unmatched slots.

    Augmenting paths let an earlier slot change its choice when a later slot
    has fewer alternatives. This avoids unnecessary repeats from greedy picks.
    """
    avoid=set(avoid);groups=[];edges=[]
    for pool in pools:
        rows=list(pool);RNG.shuffle(rows)
        if not rows:raise ValidationError('No matching questions are available.')
        group={}
        for row in rows:group.setdefault(wording_key(row),[]).append(row)
        keys=list(group);RNG.shuffle(keys)
        keys.sort(key=lambda key:key in avoid)
        groups.append(group);edges.append(keys)
    owner={};assigned={}
    def match(slot,seen,fresh_only):
        for identity in edges[slot]:
            if identity in seen or fresh_only and identity in avoid:continue
            seen.add(identity)
            if identity not in owner or match(owner[identity],seen,fresh_only):
                owner[identity]=slot;assigned[slot]=identity;return True
        return False
    for fresh_only in (True,False):
        for slot in range(len(pools)):
            if slot not in assigned:match(slot,set(),fresh_only)
    result=[None]*len(pools);records={}
    for slot,identity in assigned.items():
        row=groups[slot][identity][0];result[slot]=row;records[record_key(row)]=slot
    def match_record(slot,seen):
        # Retain every occupied record while moving its owner if needed. Thus
        # filling an exhausted wording pool cannot undo distinct wording found above.
        for identity in edges[slot]:
            for row in groups[slot][identity]:
                key=record_key(row)
                if key in seen:continue
                seen.add(key)
                if key not in records or match_record(records[key],seen):
                    records[key]=slot;result[slot]=row;return True
        return False
    for slot,row in enumerate(result):
        if row is not None:continue
        if not match_record(slot,set()):raise ValidationError('There are not enough different question records for this selection.')
    return result
