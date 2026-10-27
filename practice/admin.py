import uuid
from django.contrib import admin
from .models import Question, Keyword, Rubric, ImportLog

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id','component','question_number','part','year','active']
    list_filter = ['component','part','question_number','year','active']
    search_fields = ['id','prompt','indicative_content']
    readonly_fields = ['created_at','updated_at']
    exclude = ['data']
    list_per_page = 40
    def get_changeform_initial_data(self, request):
        return {'id':'custom-'+uuid.uuid4().hex,'series':'Admin added'}

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['term','component','pool','active']
    list_filter = ['component','pool','active']
    search_fields = ['term','definition']

@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ['id','title']
    readonly_fields = ['id','title','data']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ['created_at','actor','count','filename']
    readonly_fields = ['created_at','actor','count','filename']
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

from django import forms
from .models import SiteContent, Announcement
from .content import VisualEditor

class SiteContentForm(forms.ModelForm):
    class Meta:
        model = SiteContent
        fields = '__all__'
        widgets = {'body': VisualEditor()}

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    form = SiteContentForm
    list_display = ['key','updated_at']
    readonly_fields = ['key','updated_at']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = '__all__'
        widgets = {'body': VisualEditor()}


class SiteScopedAdmin(admin.ModelAdmin):
    def get_queryset(self,request):
        from .site_scope import site_for_request
        return super().get_queryset(request).filter(site=site_for_request(request))
    def save_model(self,request,obj,form,change):
        from .site_scope import site_for_request
        obj.site=site_for_request(request)
        super().save_model(request,obj,form,change)

@admin.register(Announcement)
class AnnouncementAdmin(SiteScopedAdmin):
    form = AnnouncementForm
    list_display = ['title','published','starts_at','ends_at','position']
    list_filter = ['published']
    search_fields = ['title','body']
    readonly_fields = ['updated_at']

from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['subject','category','status','name','created_at']
    list_filter = ['status','category','created_at']
    search_fields = ['subject','message','name','email']
    date_hierarchy = 'created_at'
    readonly_fields = ['subject','category','message','name','email','created_at']
    fields = ['subject','category','message','name','email','created_at','status','admin_notes']
    actions = ['mark_reviewing','mark_resolved']
    list_per_page = 40
    def has_add_permission(self, request): return False
    @admin.action(description='Mark selected feedback as reviewing')
    def mark_reviewing(self, request, queryset):
        self.message_user(request,f'{queryset.update(status="reviewing")} feedback responses marked as reviewing.')
    @admin.action(description='Mark selected feedback as resolved')
    def mark_resolved(self, request, queryset):
        self.message_user(request,f'{queryset.update(status="resolved")} feedback responses marked as resolved.')

from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import ResourceCollection, AdminNotification, ContentRevision, QuestionRevision, UpdatePost

class ExtendedQuestionForm(forms.ModelForm):
    change_reason = forms.CharField(required=False,max_length=500,help_text='Explain a correction. This is saved in question history.')
    class Meta:
        model = Question
        fields = '__all__'

admin.site.unregister(Question)
@admin.register(Question)
class ExtendedQuestionAdmin(QuestionAdmin):
    form = ExtendedQuestionForm
    list_display = ['id','component','question_number','part','year','source_type','collection','status','active']
    list_filter = ['status','source_type','collection','component','part','year','active']
    search_fields = ['id','prompt','indicative_content','topic_name','source_reference']
    readonly_fields = ['created_at','updated_at','preview_link','link_check_result']
    actions = ['send_for_review','publish_questions','withdraw_questions','request_link_check']
    def get_changeform_initial_data(self,request):
        return {'id':'custom-'+uuid.uuid4().hex,'series':'Admin added','source_type':'additional','status':'draft'}
    @admin.display(description='Preview')
    def preview_link(self,obj):
        return format_html('<a href="{}">Preview student question</a>',reverse('admin_preview',args=['question',obj.pk])) if obj and obj.pk else 'Save a draft to preview.'
    @admin.display(description='Source link checks')
    def link_check_result(self,obj): return str(obj.data.get('link_checks','Not checked. Use the list action to request a check.')) if obj else ''
    def save_model(self,request,obj,form,change):
        if change:
            old=Question.objects.filter(pk=obj.pk).values('prompt','indicative_content','component','question_number','part','source_reference','topic_name','status').first()
            if old: QuestionRevision.objects.create(question=obj,previous=old,reason=form.cleaned_data.get('change_reason',''))
        else:
            import re
            normal=lambda value:re.sub(r'\W+','',value.casefold())
            if any(normal(prompt)==normal(obj.prompt) for prompt in Question.objects.values_list('prompt',flat=True)):
                self.message_user(request,'An identical question already exists. Review this draft before publishing.',level='warning')
                obj.status='draft'
        super().save_model(request,obj,form,change)
    @admin.action(description='Move selected questions to awaiting review')
    def send_for_review(self,request,queryset):
        self.message_user(request,f'{queryset.update(status="review")} questions await review.')
    @admin.action(description='Publish selected questions after validation')
    def publish_questions(self,request,queryset):
        count=0
        for obj in queryset:
            obj.status='published'
            try: obj.full_clean();obj.save();count+=1
            except ValidationError as error: self.message_user(request,f'{obj.pk}: '+ '; '.join(error.messages),level='error')
        self.message_user(request,f'{count} questions published.')
    @admin.action(description='Withdraw selected questions to drafts')
    def withdraw_questions(self,request,queryset): self.message_user(request,f'{queryset.update(status="draft")} questions withdrawn.')
    @admin.action(description='Request source URL checks for selected questions')
    def request_link_check(self,request,queryset):
        for obj in queryset:
            obj.data['link_check_requested']=True;obj.save(update_fields=['data'])
        self.message_user(request,'Source checks queued. Results will appear in each question after the maintenance worker runs.')

@admin.register(ResourceCollection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['title','kind','author','chapter','permission_status','published']
    list_filter = ['published','permission_status','kind']
    search_fields = ['title','author','chapter']
    actions = ['withdraw']
    @admin.action(description='Withdraw selected collections from public practice')
    def withdraw(self,request,queryset): self.message_user(request,f'{queryset.update(published=False)} collections withdrawn. Their questions are retained.')

@admin.register(QuestionRevision)
class QuestionRevisionAdmin(admin.ModelAdmin):
    list_display = ['question','created_at','reason']
    readonly_fields = ['question','previous','reason','created_at']
    search_fields = ['question__id','reason']
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False

@admin.register(ContentRevision)
class ContentRevisionAdmin(admin.ModelAdmin):
    list_display = ['content','created_at','restore_link']
    readonly_fields = ['content','body','created_at','restore_link']
    @admin.display(description='Restore')
    def restore_link(self,obj): return format_html('<a href="{}">Review / restore this version</a>',reverse('admin_restore_content',args=[obj.pk]))
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False

@admin.register(AdminNotification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['created_at','report_link','read','emailed_at','attempts','last_error']
    list_filter = ['read','emailed_at']
    readonly_fields = ['feedback','created_at','emailed_at','attempts','last_error','next_attempt','report_link']
    actions = ['mark_read','retry_email']
    @admin.display(description='Report')
    def report_link(self,obj): return format_html('<a href="{}">Open report #{}</a>',reverse('admin:practice_feedback_change',args=[obj.feedback_id]),obj.feedback_id)
    def has_add_permission(self,request): return False
    @admin.action(description='Mark selected notifications as read')
    def mark_read(self,request,queryset): queryset.update(read=True)
    @admin.action(description='Retry undelivered notification emails')
    def retry_email(self,request,queryset): queryset.filter(emailed_at__isnull=True).update(attempts=0,next_attempt=None,last_error='')

class UpdateForm(forms.ModelForm):
    class Meta:
        model=UpdatePost
        fields='__all__'
        widgets={'body':VisualEditor()}

@admin.register(UpdatePost)
class UpdateAdmin(SiteScopedAdmin):
    form=UpdateForm
    list_display=['title','kind','published','resolved','created_at']
    list_filter=['kind','published','resolved']

# Extend the existing feedback administration without a second login surface.
FeedbackAdmin.list_display=['subject','category','priority','status','name','created_at']
FeedbackAdmin.list_filter=['status','priority','category','created_at']
FeedbackAdmin.fields=['subject','category','question','question_reference','message','name','email','created_at','priority','status','admin_notes']
FeedbackAdmin.readonly_fields+=['question','question_reference']
def feedback_change(self,request,object_id,form_url='',extra_context=None):
    if request.user.has_perm('practice.view_feedback') or request.user.has_perm('practice.change_feedback'):
        AdminNotification.objects.filter(feedback_id=object_id).update(read=True)
    return super(FeedbackAdmin,self).change_view(request,object_id,form_url,extra_context)
FeedbackAdmin.change_view=feedback_change
SiteContentAdmin.readonly_fields+=['preview_link']
SiteContentAdmin.preview_link=lambda self,obj: format_html('<a href="{}">Preview this page section</a>',reverse('admin_preview',args=['content',obj.pk])) if obj else ''
AnnouncementAdmin.readonly_fields+=['preview_link']
AnnouncementAdmin.preview_link=lambda self,obj: format_html('<a href="{}">Preview announcement</a>',reverse('admin_preview',args=['announcement',obj.pk])) if obj else ''

def bulk_edit(self,request,queryset):
    from django.core import signing
    from django.http import HttpResponseRedirect
    from urllib.parse import urlencode
    ids=list(queryset.values_list('pk',flat=True)[:501])
    if len(ids)>500:
        self.message_user(request,'Select at most 500 questions.',level='error');return
    token=signing.dumps({'user':request.user.pk,'ids':ids},salt='bulk-questions',compress=True)
    return HttpResponseRedirect(reverse('admin_bulk_questions')+'?'+urlencode({'selection':token}))
bulk_edit.short_description='Bulk edit classification, collection or publication status'
ExtendedQuestionAdmin.bulk_edit=bulk_edit
ExtendedQuestionAdmin.actions+=['bulk_edit']

from .models import Article
class ArticleForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        fmt=self.data.get('body_format') if self.is_bound else self.instance.body_format
        if fmt!='html':
            self.fields['body'].widget=forms.Textarea(attrs={'rows':30,'cols':100,'class':'markdown-source','spellcheck':'true'})
            self.fields['body'].help_text='Markdown: ## Heading, **bold**, *italic*, - list item, [link text](https://example.com). Save and use Preview article to see the rendered post. Paste Markdown directly here.'
    class Meta:
        model=Article
        fields='__all__'
        widgets={'body':VisualEditor()}

@admin.register(Article)
class ArticleAdmin(SiteScopedAdmin):
    form=ArticleForm
    list_display=['title','published','publish_at','show_in_sidebar','position','updated_at']
    list_filter=['published','show_in_sidebar']
    search_fields=['title','summary','body']
    prepopulated_fields={'slug':('title',)}
    readonly_fields=['created_at','updated_at','preview_link']
    fields=['title','slug','summary','body_format','body','published','publish_at','show_in_sidebar','position','preview_link','created_at','updated_at']
    actions=['publish_articles','unpublish_articles']
    @admin.display(description='Preview')
    def preview_link(self,obj):
        if not obj or not obj.pk:return 'Save a draft first to preview it.'
        return format_html('<a href="{}?preview=1">Preview article</a>',obj.get_absolute_url())
    @admin.action(description='Publish selected articles')
    def publish_articles(self,request,queryset):self.message_user(request,f'{queryset.update(published=True)} articles published.')
    @admin.action(description='Unpublish selected articles')
    def unpublish_articles(self,request,queryset):self.message_user(request,f'{queryset.update(published=False)} articles returned to drafts.')

from .models import FAQ
class FAQForm(forms.ModelForm):
    class Meta:
        model=FAQ
        fields='__all__'
        widgets={'answer':VisualEditor()}

@admin.register(FAQ)
class FAQAdmin(SiteScopedAdmin):
    form=FAQForm
    list_display=['question','category','published','position','updated_at']
    list_filter=['published','category']
    search_fields=['question','answer']
    list_editable=['position']
    readonly_fields=['updated_at']
    fields=['question','category','answer','position','published','updated_at']
    actions=['publish_faqs','unpublish_faqs']
    @admin.action(description='Publish selected FAQs')
    def publish_faqs(self,request,queryset):self.message_user(request,f'{queryset.update(published=True)} FAQs published.')
    @admin.action(description='Unpublish selected FAQs')
    def unpublish_faqs(self,request,queryset):self.message_user(request,f'{queryset.update(published=False)} FAQs returned to drafts.')

# Only send acknowledgements/status emails when the sender explicitly opted in.
FeedbackAdmin.fields.insert(FeedbackAdmin.fields.index('created_at'),'email_updates')
def notify_feedback_status(self,request,obj):
    from .email_jobs import feedback_email
    if not obj.email_updates:return
    try:feedback_email(obj,'feedback_status')
    except Exception:self.message_user(request,f'Report #{obj.pk} was updated, but its email could not be queued.',level='warning')
def feedback_save_model(self,request,obj,form,change):
    previous=Feedback.objects.filter(pk=obj.pk).values_list('status',flat=True).first() if change else None
    super(FeedbackAdmin,self).save_model(request,obj,form,change)
    if previous is not None and previous!=obj.status:notify_feedback_status(self,request,obj)
FeedbackAdmin.save_model=feedback_save_model

def set_feedback_status(self,request,queryset,status):
    count=0
    for obj in queryset.exclude(status=status):
        obj.status=status;obj.save(update_fields=['status']);count+=1
        notify_feedback_status(self,request,obj)
    self.message_user(request,f'{count} feedback responses updated. Status emails are queued only for opted-in senders.')
def mark_reviewing_with_email(self,request,queryset):set_feedback_status(self,request,queryset,'reviewing')
def mark_resolved_with_email(self,request,queryset):set_feedback_status(self,request,queryset,'resolved')
mark_reviewing_with_email.short_description='Mark as reviewing and notify opted-in senders'
mark_resolved_with_email.short_description='Mark as resolved and notify opted-in senders'
FeedbackAdmin.mark_reviewing=mark_reviewing_with_email
FeedbackAdmin.mark_resolved=mark_resolved_with_email
