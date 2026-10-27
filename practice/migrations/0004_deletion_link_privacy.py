from django.db import migrations

def update_privacy(apps, schema_editor):
    Content = apps.get_model('practice', 'SiteContent')
    row = Content.objects.filter(key='about').first()
    if row is None: return
    old = 'You can delete the snapshot early using “Delete shared answers” in the tab that created it. If you clear or close the tab, automatic expiry still applies.'
    new = 'You can delete the snapshot early using “Delete shared answers” in the tab that created it. Save the separate private deletion link by copying it, downloading its details, or emailing yourself a draft. You can use that private link at /s/manage/ after the original tab has closed, without an account. Anyone with the private deletion link can delete the submission, so keep it separate from the viewing link sent to your teacher. The website does not collect your email address. If you lose the private deletion link, automatic expiry still applies.'
    if old in row.body: row.body = row.body.replace(old,new)
    else: row.body += '<h2>Deleting shared submissions later</h2><p>'+new+'</p>'
    row.save(update_fields=['body'])

class Migration(migrations.Migration):
    dependencies = [('practice','0003_website_content')]
    operations = [migrations.RunPython(update_privacy, migrations.RunPython.noop)]
