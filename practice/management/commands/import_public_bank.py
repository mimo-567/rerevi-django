"""Import the public, allowlisted RE revision snapshot."""
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from practice.models import Question,Keyword,Rubric,ResourceCollection

class Command(BaseCommand):
    help='Load bundled public questions, keywords and rubrics, preserving existing admin edits.'

    @transaction.atomic
    def handle(self,*args,**options):
        data=json.loads((settings.BASE_DIR/'practice/data/public_bank.json').read_text())
        if data.get('format')!='rerevi.public-bank' or data.get('version')!=1:
            raise CommandError('Unsupported public bank format.')
        for key,model in [('collections',ResourceCollection),('rubrics',Rubric),('keywords',Keyword),('questions',Question)]:
            created=0
            for row in data[key]:
                row=dict(row)
                pk=row.pop('id')
                obj,new=model.objects.get_or_create(pk=pk,defaults=row)
                if new:
                    obj.full_clean()
                    created+=1
            self.stdout.write(f'{key}: {created} added; existing records preserved.')
