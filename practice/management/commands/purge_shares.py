from django.core.management.base import BaseCommand
from practice.sharing import purge_expired
class Command(BaseCommand):
    help='Delete expired answer snapshots. Run hourly; snapshots are never part of database backups.'
    def handle(self,*args,**options):
        self.stdout.write(f'Deleted {purge_expired()} expired answer snapshots.')
