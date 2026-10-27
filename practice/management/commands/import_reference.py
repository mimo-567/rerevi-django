import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from practice.models import Question, Keyword, Rubric

class Command(BaseCommand):
    help='Import official reference JSON without overwriting admin edits on repeat runs.'
    def add_arguments(self, parser): parser.add_argument('directory')
    @transaction.atomic
    def handle(self, *args, **options):
        root=Path(options['directory'])
        marking=json.loads((root/'marking_guides.json').read_text())
        for r in marking['rubrics']:
            Rubric.objects.get_or_create(id=r['id'],defaults={'title':r['id'].replace('eduqas_','').replace('_',' ').upper(),'data':r})
        qs=json.loads((root/'past_papers/question_bank.json').read_text())['questions']
        n=0
        for q in qs:
            obj,created=Question.objects.get_or_create(id=q['id'],defaults={'component':q['component'],'question_number':q['question_number'],'part':q['part'],'prompt':q['prompt'],'indicative_content':q['indicative_content_text'],'year':q['year'],'series':q['series'],'source_url':q.get('source_url',''),'mark_scheme_url':q.get('mark_scheme_url',''),'data':q})
            obj.full_clean();n+=int(created)
        keys=json.loads((root/'key_concepts.json').read_text())
        for group in keys['groups']:
            for k in group['concepts']:
                obj,_=Keyword.objects.get_or_create(component=group['component'],pool=group['topic'],term=k['term'],defaults={'definition':k['indicative_content'],'source_url':keys['source']['url'],'source_page':k.get('source_pdf_page')})
                obj.full_clean()
        self.stdout.write(self.style.SUCCESS(f'Imported {n} new questions. Bank: {Question.objects.count()} questions, {Keyword.objects.count()} keywords.'))
