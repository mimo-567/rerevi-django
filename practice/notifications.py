"""Owner SMTP configuration and durable notification delivery queue."""
import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db.models import Q
from django.utils import timezone
from .models import AdminNotification

MAIL_DIR=settings.DATA_DIR/'mail'

def mail_config():
    try: return json.loads((MAIL_DIR/'settings.json').read_text())
    except (FileNotFoundError,ValueError): return {'enabled':False}

def save_mail_config(enabled,password):
    MAIL_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    old=mail_config()
    data={'enabled':bool(enabled),'password':password or old.get('password','')}
    if data['enabled'] and not data['password']: raise ValueError('Enter the Forward Email alias password before enabling email.')
    with tempfile.NamedTemporaryFile(dir=MAIL_DIR,mode='w',delete=False) as handle:
        temporary=Path(handle.name)
        try:
            json.dump(data,handle);handle.flush();os.fsync(handle.fileno())
            os.chmod(temporary,0o600);os.replace(temporary,MAIL_DIR/'settings.json')
        finally: temporary.unlink(missing_ok=True)

def connection():
    config=mail_config()
    if not config.get('enabled') or not config.get('password'): return None
    if not settings.SMTP_USERNAME or not settings.SMTP_OWNER:return None
    return get_connection('django.core.mail.backends.smtp.EmailBackend',host=settings.SMTP_HOST,port=settings.SMTP_PORT,username=settings.SMTP_USERNAME,password=config['password'],use_ssl=settings.SMTP_SSL,use_tls=settings.SMTP_TLS,timeout=12)

def deliver_pending():
    conn=connection()
    if conn is None: return 0
    now=timezone.now();sent=0
    pending=AdminNotification.objects.filter(emailed_at__isnull=True,attempts__lt=10).filter(Q(next_attempt__isnull=True)|Q(next_attempt__lte=now)).select_related('feedback').order_by('created_at')[:10]
    for notice in pending:
        # systemd runs one worker at a time; delivered messages are marked only after SMTP accepts them.
        try:
            item=notice.feedback
            body=f'A new {item.get_category_display().lower()} was reported on RE Revi.\n\nReport #{item.pk}\nSubject: {item.subject}\nSubmitted: {item.created_at.isoformat()}\n\nRead and manage it securely in admin:\n{settings.PUBLIC_BASE_URL}/admin/practice/feedback/{item.pk}/change/\n\nThis notification does not include submitted answers or the feedback sender email.'
            EmailMessage(f'RE Revi: new report #{item.pk}',body,'RE Revi <'+settings.SMTP_FROM+'>',[settings.SMTP_OWNER],connection=conn).send(fail_silently=False)
            notice.emailed_at=timezone.now();notice.last_error='';sent+=1
        except Exception:
            notice.last_error='SMTP delivery failed. Check alias credentials, outbound SMTP access and Forward Email configuration.'
            notice.next_attempt=timezone.now()+timedelta(minutes=min(60,2**min(notice.attempts,6)))
        notice.attempts+=1
        notice.save(update_fields=['emailed_at','last_error','next_attempt','attempts'])
    return sent
