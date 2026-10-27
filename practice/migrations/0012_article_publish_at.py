from django.db import migrations,models

class Migration(migrations.Migration):
    dependencies=[('practice','0011_article_body_format')]
    operations=[migrations.AddField(model_name='article',name='publish_at',field=models.DateTimeField(blank=True,null=True,help_text='Optional publication time (Europe/London). Enable Published to schedule; leave blank to publish immediately.'))]
