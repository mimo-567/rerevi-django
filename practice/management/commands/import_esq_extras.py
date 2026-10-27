import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from practice.models import Question,ResourceCollection,SiteContent

class Command(BaseCommand):
    help='Import the owner-supplied C1 ESQ B/C/D questions and original C2/C3 additional practice. Never imports A.'
    @transaction.atomic
    def handle(self,*args,**options):
        data=json.loads((Path(__file__).resolve().parents[2]/'data'/'esq_extra_questions.json').read_text())
        collections={}
        for source in data['collections']:
            collection,created=ResourceCollection.objects.get_or_create(title=source['title'],defaults={'kind':source['kind'],'author':source['author'],'source_url':source.get('reference_url',''),'permission_status':'allowed','permission_notes':'Publication requested by site owner for this supplied/original practice pack. No public permission statement is made.','published':True})
            collections[source['key']]=collection
        created=0;existing=0
        for item in data['questions']:
            if item['part'] not in ('b','c','d'): raise ValueError('This pack must not contain Part A questions.')
            if Question.objects.filter(pk=item['id']).exists(): existing+=1;continue
            collection=collections[item['collection']]
            question=Question(id=item['id'],component=item['component'],question_number=item['number'],part=item['part'],prompt=item['prompt'],indicative_content='',source_type='additional',collection=collection,source_reference=item['source_reference'],topic_name=item['topic_name'],status='published' if collection.published and collection.permission_status=='allowed' else 'draft',series='Additional ESQ practice',source_url='',data=item['data'])
            question.full_clean();question.save();created+=1
        page=SiteContent.objects.filter(key='about').first()
        if page:
            old='B, C and D use past-paper questions with matching indicative content.'
            new='B, C and D can use official past-paper questions with matching indicative content, or labelled additional practice without question-specific indicative content. You can exclude additional practice. Extra Part A questions from the ESQ resources are not used.'
            if old in page.body:
                page.body=page.body.replace(old,new);page.save()
        self.stdout.write(self.style.SUCCESS(f'Imported {created} extra B/C/D questions; {existing} existing records preserved. Source Part A excluded: {data["excluded_a"]}; duplicate removed: {data["duplicates_removed"]}.'))
