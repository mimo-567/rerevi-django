from django.db import migrations, models

def rename_series(apps,schema_editor):
    apps.get_model('practice','Question').objects.filter(series='Teacher added').update(series='Admin added')

class Migration(migrations.Migration):
    dependencies=[('practice','0001_initial')]
    operations=[migrations.AlterField(model_name='question',name='series',field=models.CharField(default='Admin added',max_length=40)),migrations.RunPython(rename_series,migrations.RunPython.noop)]
