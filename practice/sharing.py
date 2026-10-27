"""Expiring answer snapshots, kept outside the backed-up question database."""
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import tempfile
from datetime import timedelta, datetime
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .services import paper_from_token
TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{43}$')
LIFETIMES = (1, 7, 14, 29)
MAX_ANSWER_BYTES = 250_000

class SharingFull(Exception): pass

def _path(token):
    if not isinstance(token,str) or not TOKEN_RE.fullmatch(token): return None
    return settings.SHARE_DIR / (hashlib.sha256(token.encode()).hexdigest()+'.json')

def load_share(token):
    path=_path(token)
    if path is None: return None
    try:
        data=json.loads(path.read_text())
        expiry=datetime.fromisoformat(data['expires_at'])
        if timezone.is_naive(expiry) or expiry<=timezone.now():
            path.unlink(missing_ok=True);return None
        return data
    except (FileNotFoundError,ValueError,KeyError,TypeError):
        if path.exists(): path.unlink(missing_ok=True)
        return None

def _scores(raw, allowed, maxima):
    if not isinstance(raw,dict): raise ValidationError('Self marks must be an object.')
    result={}
    for key,value in raw.items():
        if key not in allowed: continue
        if type(value) is not int or not 0<=value<=maxima[key]: raise ValidationError('A self mark is outside its allowed range.')
        result[key]=value
    return result

def create_share(options):
    if options.get('consent') is not True: raise ValidationError('Confirm that you want to store and share your answers.')
    days=options.get('days',7)
    if type(days) is not int or days not in LIFETIMES: raise ValidationError('Choose 1, 7, 14 or 29 days.')
    token=options.get('paper_token','')
    if not isinstance(token,str) or len(token)>200000: raise ValidationError('Invalid paper token.')
    paper=paper_from_token(token)
    raw_answers=options.get('answers',{})
    if not isinstance(raw_answers,dict): raise ValidationError('Answers must be an object.')
    allowed={q['kind']+':'+q['id'] for q in paper['questions']}
    answers={}
    for key,value in raw_answers.items():
        if key not in allowed: continue
        if not isinstance(value,str) or len(value)>30000: raise ValidationError('An answer is too long.')
        answers[key]=value
    if not any(value.strip() for value in answers.values()): raise ValidationError('Type at least one answer before making a sharing link.')
    if sum(len(v.encode('utf-8')) for v in answers.values())>MAX_ANSWER_BYTES: raise ValidationError('These answers are too large to share. Download them and attach the file to your email instead.')
    name=options.get('name','')
    if not isinstance(name,str) or len(name)>100: raise ValidationError('Your name must be 100 characters or fewer.')
    maxima={q['kind']+':'+q['id']:q['marks'] for q in paper['questions']}
    spag_max={q['kind']+':'+q['id']:q['spag'] for q in paper['questions'] if q['spag']}
    marks=_scores(options.get('marks',{}),allowed,maxima)
    spag=_scores(options.get('spag_marks',{}),set(spag_max),spag_max)
    root=settings.SHARE_DIR
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if len(list(root.glob('*.json')))>=1000 or shutil.disk_usage(root).free<256*1024*1024: raise SharingFull
    now=timezone.now();expiry=now+timedelta(days=days)
    access_token=secrets.token_urlsafe(32);delete_token=secrets.token_urlsafe(32)
    questions=[]
    for q in paper['questions']:
        k=q['kind']+':'+q['id']
        questions.append({'prompt':q['prompt'],'topic':q['topic'],'part':q['part'],'marks':q['marks'],'spag':q['spag'],'answer':answers.get(k,''),'self_mark':marks.get(k),'spag_mark':spag.get(k)})
    snapshot={'subject':paper.get('subject','re'),'areas':sorted({q.get('area','') for q in paper['questions']}),'version':1,'created_at':now.isoformat(),'expires_at':expiry.isoformat(),'name':name.strip(),'title':paper['title'],'component_name':paper['component_name'],'total_marks':paper['total_marks'],'questions':questions,'delete_hash':hashlib.sha256(delete_token.encode()).hexdigest()}
    encoded=json.dumps(snapshot,ensure_ascii=False).encode('utf-8')
    if len(encoded)>512000: raise ValidationError('This snapshot is too large. Save your answers as a file instead.')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=root,suffix='.tmp',delete=False) as handle:
            temporary=Path(handle.name);handle.write(encoded);handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,_path(access_token))
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    base=settings.PUBLIC_BASE_URL
    return {'token':access_token,'delete_token':delete_token,'deletion_url':base+'/s/manage/#'+access_token+'.'+delete_token,'url':base+'/s/'+access_token+'/','expires_at':expiry.isoformat(),'days':days}

def delete_share(token,delete_token):
    if not isinstance(delete_token,str) or not TOKEN_RE.fullmatch(delete_token): return False
    data=load_share(token)
    if data is None: return False
    digest=hashlib.sha256(delete_token.encode()).hexdigest()
    if not hmac.compare_digest(digest,data.get('delete_hash','')): return False
    _path(token).unlink(missing_ok=True)
    return True

def purge_expired():
    from .email_jobs import purge_email_jobs
    purge_email_jobs()
    root=settings.SHARE_DIR
    if not root.exists(): return 0
    now=timezone.now();deleted=0
    for path in root.iterdir():
        if not path.is_file() or path.suffix not in ('.json','.tmp'): continue
        try:
            age=now.timestamp()-path.stat().st_mtime
            remove=age>=29*86400
            if path.suffix=='.tmp': remove=age>=3600
            elif not remove:
                data=json.loads(path.read_text());expiry=datetime.fromisoformat(data['expires_at'])
                remove=timezone.is_naive(expiry) or expiry<=now
            if remove: path.unlink(missing_ok=True);deleted+=1
        except FileNotFoundError: continue
        except (ValueError,KeyError,TypeError): path.unlink(missing_ok=True);deleted+=1
    return deleted
