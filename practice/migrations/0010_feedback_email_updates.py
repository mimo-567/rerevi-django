from django.db import migrations,models

def explain_email(apps,schema_editor):
    Content=apps.get_model('practice','SiteContent')
    Revision=apps.get_model('practice','ContentRevision')
    page=Content.objects.filter(key='about').first()
    if page:
        Revision.objects.create(content=page,body=page.body)
        page.body+='<h2>Optional transactional emails</h2><p>You can explicitly request a shared-submission receipt from ReRevi by entering your own email address and pressing the send button. It contains the viewing link, private deletion link and submission/expiry dates, but no answers. Keep the receipt private. The recipient address is not added to the submission manager or answer snapshot.</p><p>You can separately opt in on the feedback form to receive an acknowledgement and updates when the report status changes. A reply email alone does not opt you in; existing feedback records are not subscribed. The administrator can disable feedback updates on request. These emails contain a report reference and status, not answer text or the feedback message. Teacher-feedback buttons still prepare a draft in your own email application for you to send.</p><p>Forward Email processes messages sent by this server. Requested user emails are temporarily queued outside database backups, with their recipient and message, and are removed after the SMTP provider accepts them or after 24 hours. Deleting a share or withdrawing feedback email consent prevents pending jobs from being sent when the worker next checks them. Receipt copies in your mailbox are outside the server deletion process. Email requests use short-lived keyed connection/recipient hashes to enforce rate limits.</p>'
        page.save(update_fields=['body'])
    FAQ=apps.get_model('practice','FAQ')
    for question in ['Can I send a suggestion without an email address?']:
        faq=FAQ.objects.filter(question=question).first()
        if faq:
            faq.answer+='<p>If you supply your own reply email, you can separately tick the optional box to receive a receipt and report status updates. Entering a reply address without checking that box does not subscribe you.</p>'
            faq.save(update_fields=['answer'])
    FAQ.objects.create(question='Can ReRevi email my private submission receipt?',category='Sharing and privacy',position=70,published=True,answer='<p>Yes. After creating a sharing link, enter your own address in the server-sent receipt field and press Send my private receipt from ReRevi. It includes the private deletion link, so keep it separate from the teacher viewing link. No answers are included. You can still download a receipt or prepare an email draft yourself.</p>')
    FAQ.objects.create(question='How do feedback email updates work?',category='Troubleshooting and feedback',position=70,published=True,answer='<p>Supply your own reply email and tick Email me a receipt and status updates on the feedback form. ReRevi queues an acknowledgement, then sends an update when the administrator changes the report status. Existing reports are not automatically subscribed. To stop updates, contact support with your feedback reference.</p>')
    FAQ.objects.create(question='Why has my ReRevi email not arrived?',category='Troubleshooting and feedback',position=80,published=True,answer='<p>Sending is queued and normally attempted within a minute. Check your spam folder and the address you entered. Delivery may be delayed or fail; queued user emails expire after 24 hours. Keep a downloaded deletion receipt as a backup. Rate limits may require you to wait before requesting another email. Contact support if the problem continues.</p>')

class Migration(migrations.Migration):
    dependencies=[('practice','0009_faq')]
    operations=[migrations.AddField(model_name='feedback',name='email_updates',field=models.BooleanField(default=False,help_text='Sender consent for an acknowledgement and feedback status updates.')),migrations.RunPython(explain_email,migrations.RunPython.noop)]
