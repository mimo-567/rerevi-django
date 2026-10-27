from django.db import migrations, models

def update_privacy(apps, schema_editor):
    Content = apps.get_model('practice','SiteContent')
    row = Content.objects.filter(key='about').first()
    if row:
        row.body += '<h2>Submission moderation and website feedback</h2><p>The site owner can see the optional name and submission date of active shared submissions and permanently delete them. The administration interface does not provide submitted answers or sharing/deletion links.</p><p>The feedback form stores your message, category, subject, optional name and optional reply email for the administrator. Feedback is not public. It is kept until deleted by the administrator and may remain in database backups for up to 30 days afterwards. This is separate from the shared-answer deletion policy. A short-lived keyed hash of your connection address is used to limit repeated feedback submissions; your address is not stored in the feedback record. Feedback does not automatically send an email. For privacy requests, contact rerevi@zafirshirazi.com.</p>'
        row.save(update_fields=['body'])

class Migration(migrations.Migration):
    dependencies = [('practice','0004_deletion_link_privacy')]
    operations = [migrations.CreateModel(name='Feedback',fields=[
        ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
        ('name',models.CharField(max_length=100,blank=True)),
        ('email',models.EmailField(max_length=254,blank=True,help_text='Optional reply address supplied by the sender.')),
        ('category',models.CharField(max_length=20,choices=[('suggestion','Suggestion'),('problem','Website problem'),('content','Question or marking correction'),('other','Other')])),
        ('subject',models.CharField(max_length=150)),
        ('message',models.TextField(max_length=4000)),
        ('created_at',models.DateTimeField(auto_now_add=True)),
        ('status',models.CharField(max_length=20,choices=[('new','New'),('reviewing','Reviewing'),('resolved','Resolved')],default='new',db_index=True)),
        ('admin_notes',models.TextField(blank=True,max_length=10000,help_text='Internal notes; not shown to the sender.')),
    ],options={'ordering':['-created_at'],'verbose_name_plural':'Feedback'}),migrations.RunPython(update_privacy,migrations.RunPython.noop)]
