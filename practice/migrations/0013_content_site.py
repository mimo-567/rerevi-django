from django.db import migrations,models

def assign_sites(apps,schema_editor):
    for name,title in [('Article','title'),('FAQ','question'),('Announcement','title'),('UpdatePost','title')]:
        model=apps.get_model('practice',name)
        for row in model.objects.all():
            text=getattr(row,title,'')+' '+getattr(row,'category','')
            if 'engrevi' in text.lower() or 'english' in text.lower():
                model.objects.filter(pk=row.pk).update(site='english')

class Migration(migrations.Migration):
    dependencies=[('practice','0012_article_publish_at')]
    operations=[migrations.AddField(model_name=name,name='site',field=models.CharField(choices=[('re','ReRevi'),('english','EngRevi')],db_index=True,default='re',editable=False,max_length=10)) for name in ['article','faq','announcement','updatepost']]+[migrations.RunPython(assign_sites,migrations.RunPython.noop)]
