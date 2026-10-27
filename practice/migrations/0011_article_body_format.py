from django.db import migrations,models


def preserve_existing(apps,schema_editor):
    # All pre-existing articles were saved by the HTML visual editor.
    apps.get_model('practice','Article').objects.all().update(body_format='html')


class Migration(migrations.Migration):
    dependencies=[('practice','0010_feedback_email_updates')]
    operations=[
        migrations.AddField(model_name='article',name='body_format',field=models.CharField(choices=[('markdown','Markdown'),('html','Visual editor (existing HTML)')],default='markdown',help_text='Use Markdown for new blog posts. Existing visual posts can keep their HTML format.',max_length=10)),
        migrations.RunPython(preserve_existing,migrations.RunPython.noop),
    ]
