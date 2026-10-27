from django.db import migrations

def describe_release(apps,schema_editor):
    Content=apps.get_model('practice','SiteContent')
    Revision=apps.get_model('practice','ContentRevision')
    Question=apps.get_model('practice','Question')
    # Existing manually added questions are additional practice and need review.
    Question.objects.filter(id__startswith='custom-').update(source_type='additional',status='draft')
    row=Content.objects.filter(key='about').first()
    if row:
        Revision.objects.create(content=row,body=row.body)
        row.body+='<h2>Portable worksheets, local templates and notifications</h2><p>The worksheet workspace lets you export a practice file and optionally include answers, plans and self-marks. These files remain on your device unless you choose to send them elsewhere. Private sharing and deletion keys are excluded. Reopening an imported file preserves its saved wording; correction notices do not silently replace it. Files are unverified practice snapshots, not official examination papers.</p><p>Worksheet templates store settings and question identifiers in local browser storage until you delete them. They do not store answers. The current worksheet and its optional sharing details use session storage. PDF downloads send the worksheet questions, source details and guidance to this server for processing; typed answers and plans are excluded.</p><p>Selective answer sharing uploads only the selected questions, answers and self-marks with the optional name and submission label. Plans are not shared. The existing 30-day shared-answer deletion policy applies. Saving a private submission receipt lets you delete the snapshot later.</p><p>Feedback creates an unread admin notification. When owner email notifications are enabled, Forward Email processes a notification sent from rerevi@zafirshirazi.com to the owner. The notification contains the report number, category, subject and administration link. Submitted answers, feedback message text and sender contact details are excluded.</p>'
        row.save(update_fields=['body'])
    Post=apps.get_model('practice','UpdatePost')
    Post.objects.create(kind='change',title='Worksheet workspace and report notifications',body='<p>Save and reopen exact practice files, build custom worksheets from mixed topics and resource collections, download answer booklets and marking packs, preview selective sharing and keep a private deletion receipt.</p><p>Administration now includes draft import review, publication checks, bulk editing, content history, previews and an unread report inbox. Owner email notifications can be enabled in admin.</p>',published=True)

class Migration(migrations.Migration):
    dependencies=[('practice','0006_resourcecollection_updatepost_feedback_priority_and_more')]
    operations=[migrations.RunPython(describe_release,migrations.RunPython.noop)]
