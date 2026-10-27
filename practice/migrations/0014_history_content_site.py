from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[('practice','0013_content_site')]
    operations=[migrations.AlterField(model_name=name,name='site',field=models.CharField(choices=[('re','ReRevi'),('english','EngRevi'),('history','HiRevi')],db_index=True,default='re',editable=False,max_length=10)) for name in ['article','faq','announcement','updatepost']]
