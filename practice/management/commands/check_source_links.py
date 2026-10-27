from django.core.management.base import BaseCommand
from practice.link_checks import check_pending
class Command(BaseCommand):
    help='Check queued question source links.'
    def handle(self,*args,**kwargs): self.stdout.write(f'Checked {check_pending()} question source records.')
