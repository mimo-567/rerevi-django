from django.core.management.base import BaseCommand
from practice.notifications import deliver_pending
from practice.email_jobs import deliver_email_jobs
class Command(BaseCommand):
    help='Deliver queued owner report emails; retries failures without blocking feedback submission.'
    def handle(self,*args,**kwargs): self.stdout.write(f'Delivered {deliver_pending()} owner notification(s) and {deliver_email_jobs()} requested user email(s).')
