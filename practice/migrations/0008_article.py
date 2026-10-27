from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('practice','0007_workspace_privacy')]
    operations=[migrations.CreateModel(name='Article',fields=[
        ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
        ('title',models.CharField(max_length=200)),
        ('slug',models.SlugField(max_length=180,unique=True,help_text='The article address. Keep this unchanged after sharing the link.')),
        ('summary',models.CharField(max_length=300,blank=True)),
        ('body',models.TextField(max_length=50000)),
        ('published',models.BooleanField(default=False,help_text='Drafts are visible only through the admin preview.')),
        ('show_in_sidebar',models.BooleanField(default=True,help_text='Show a link in the sidebar when published.')),
        ('position',models.PositiveSmallIntegerField(default=0,help_text='Lower numbers appear first.')),
        ('created_at',models.DateTimeField(auto_now_add=True)),
        ('updated_at',models.DateTimeField(auto_now=True)),
    ],options={'ordering':['position','title']})]
