"""Short-lived transactional mail queue, outside database backups."""
import fcntl
import json
import os
import secrets
import tempfile
from pathlib import Path
from datetime import datetime,timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import EmailMessage
from django.utils import timezone
from django.utils.crypto import salted_hmac

KINDS={'share_receipt','feedback_received','feedback_status'}

def directory():
    root=settings.SHARE_DIR/'mail'
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    return root

def write_job(path,job):
    with tempfile.NamedTemporaryFile(dir=path.parent,mode='w',suffix='.tmp',delete=False) as handle:
        temporary=Path(handle.name)
        try:
            json.dump(job,handle);handle.flush();os.fsync(handle.fileno())
            os.chmod(temporary,0o600);os.replace(temporary,path)
        finally:temporary.unlink(missing_ok=True)

def queue_email(kind,recipient,body,*,address=None,share_token=None,feedback_id=None):
    from .notifications import mail_config
    if kind not in KINDS:raise ValueError('Unknown email type.')
    config=mail_config()
    if not config.get('enabled') or not config.get('password'):raise ValidationError('Email is currently unavailable. Save your receipt as a file instead.')
    if not isinstance(recipient,str):raise ValidationError('Enter a valid email address.')
    recipient=recipient.strip()
    if len(recipient)>254:raise ValidationError('Enter a valid email address.')
    validate_email(recipient)
    root=directory();now=timezone.now()
    # This lock protects the queue cap and rate checks across web/worker processes.
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if len(list(root.glob('*.json')))>=1000:raise ValidationError('Email is temporarily busy. Download your receipt and try again later.')
        keys=[('mail-to:'+salted_hmac('mail-recipient',recipient.casefold()).hexdigest(),5)]
        if address:keys.append(('mail-from:'+salted_hmac('mail-address',address).hexdigest(),10))
        timestamps={}
        for key,limit in keys:
            recent=[stamp for stamp in cache.get(key,[]) if stamp>now.timestamp()-3600]
            if len(recent)>=limit:raise ValidationError('Email request limit reached. Try again in an hour or save a receipt file.')
            timestamps[key]=recent
        job={'version':1,'kind':kind,'recipient':recipient,'body':body,'created_at':now.isoformat(),'expires_at':(now+timedelta(hours=24)).isoformat(),'attempts':0,'next_attempt':now.isoformat(),'share_token':share_token,'feedback_id':feedback_id}
        write_job(root/(secrets.token_hex(24)+'.json'),job)
        for key,recent in timestamps.items():cache.set(key,recent+[now.timestamp()],3600)
    return True

def purge_email_jobs():
    root=directory();now=timezone.now();removed=0
    for path in root.iterdir():
        if path.suffix not in ('.json','.tmp'):continue
        try:
            age=now.timestamp()-path.stat().st_mtime
            if path.suffix=='.tmp':expired=age>3600
            else:
                job=json.loads(path.read_text());expiry=datetime.fromisoformat(job['expires_at'])
                expired=timezone.is_naive(expiry) or expiry<=now or age>=86400
            if expired:path.unlink(missing_ok=True);removed+=1
        except FileNotFoundError:continue
        except (ValueError,TypeError,KeyError):path.unlink(missing_ok=True);removed+=1
    return removed

def outbox_counts():
    root=directory();queued=0;retrying=0
    for path in root.glob('*.json'):
        try:
            job=json.loads(path.read_text());queued+=1;retrying+=int(job.get('attempts',0)>0)
        except (FileNotFoundError,ValueError,TypeError):continue
    return {'queued':queued,'retrying':retrying}

def deliver_email_jobs():
    purge_email_jobs()
    from .notifications import connection
    conn=connection()
    if conn is None:return 0
    now=timezone.now();sent=0;attempted=0
    titles={'share_receipt':'RE Revi — your private submission receipt','feedback_received':'RE Revi — feedback received','feedback_status':'RE Revi — feedback status update'}
    for path in sorted(directory().glob('*.json')):
        if attempted>=20:break
        try:
            job=json.loads(path.read_text())
            if job.get('kind') not in KINDS:path.unlink(missing_ok=True);continue
            if job.get('share_token'):
                from .sharing import load_share
                if load_share(job['share_token']) is None:path.unlink(missing_ok=True);continue
            if job.get('feedback_id'):
                from .models import Feedback
                if not Feedback.objects.filter(pk=job['feedback_id'],email_updates=True,email=job['recipient']).exists():path.unlink(missing_ok=True);continue
            if job['attempts']>=6 or datetime.fromisoformat(job['next_attempt'])>now:continue
            attempted+=1
            try:
                brand='RE Revi'
                delivered=EmailMessage(titles[job['kind']].replace('RE Revi',brand),job['body'],brand+' <'+settings.SMTP_FROM+'>',[job['recipient']],connection=conn).send(fail_silently=False)
                if not delivered:raise RuntimeError('Mail not accepted')
                path.unlink(missing_ok=True);sent+=1
            except Exception:
                job['attempts']+=1
                job['next_attempt']=(timezone.now()+timedelta(minutes=2**job['attempts'])).isoformat()
                write_job(path,job)
        except FileNotFoundError:continue
        except (ValueError,KeyError,TypeError):path.unlink(missing_ok=True)
    return sent

def feedback_email(report,kind,address=None):
    if not report.email_updates or not report.email:return False
    text=('Your feedback has been received.' if kind=='feedback_received' else 'The status of your feedback has changed.')
    brand='RE Revi'
    base=settings.PUBLIC_BASE_URL
    body=f'{text}\n\nReference: {brand} feedback #{report.pk}\nStatus: {report.get_status_display()}\n\nYou opted in to email updates when submitting feedback. This email does not include your feedback text or answers.\nFor help or to stop updates, contact {settings.SUPPORT_EMAIL} and quote your reference.\n\n{base}/updates/'
    return queue_email(kind,report.email,body,address=address,feedback_id=report.pk)
