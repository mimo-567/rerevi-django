from django.core.exceptions import ValidationError
from django.db import models
from .catalogue import COMPONENT_CHOICES, COMPONENTS, MARKS

class Rubric(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    title = models.CharField(max_length=200)
    data = models.JSONField(default=dict)
    def __str__(self): return self.title

class ResourceCollection(models.Model):
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20,choices=[('teacher','Teacher resource'),('textbook','Textbook'),('other','Other')],default='teacher')
    author = models.CharField(max_length=200,blank=True)
    edition = models.CharField(max_length=100,blank=True)
    chapter = models.CharField(max_length=200,blank=True)
    source_url = models.URLField(blank=True)
    permission_status = models.CharField(max_length=20,choices=[('pending','Not yet confirmed'),('allowed','Reproduction permitted'),('restricted','Do not publish')],default='pending')
    permission_notes = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    class Meta:
        ordering = ['title']
    def clean(self):
        if self.published and self.permission_status!='allowed': raise ValidationError('Confirm reproduction permission before publishing a collection.')
    def __str__(self): return self.title

class Question(models.Model):
    id = models.CharField(primary_key=True, max_length=150)
    component = models.CharField(max_length=50, choices=COMPONENT_CHOICES, db_index=True, blank=True)
    question_number = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Component 1: theme 1–4. Christianity/Islam: 1 beliefs, 2 practices.')
    part = models.CharField(max_length=1, blank=True, choices=[('a','A · Additional keyword · 2 marks'),('b','B · Describe · 5 marks'),('c','C · Explain · 8 marks'),('d','D · Discuss · 15 marks')])
    prompt = models.TextField(help_text='For D, include the statement and question instructions. Part A belongs in Keywords.')
    indicative_content = models.TextField(blank=True, help_text='Optional for additional practice. Leave blank when no question-specific guidance was supplied.')
    source_type = models.CharField(max_length=20, choices=[('official','Official past paper'),('additional','Additional practice')], default='official', db_index=True)
    collection = models.ForeignKey(ResourceCollection, null=True, blank=True, on_delete=models.PROTECT)
    source_reference = models.CharField(max_length=200, blank=True, help_text='Original page, chapter or worksheet question label.')
    topic_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=[('draft','Draft'),('review','Awaiting review'),('published','Published')], default='published', db_index=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    series = models.CharField(max_length=40, default='Admin added')
    source_url = models.URLField(blank=True)
    mark_scheme_url = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    data = models.JSONField(default=dict, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['component','question_number','part','-year','id']
        indexes = [models.Index(fields=['component','question_number','part','active'])]
    def clean(self):
        if not self.prompt.strip(): raise ValidationError({'prompt':'Enter the question text.'})
        if self.status=='published':
            if self.component not in COMPONENTS: raise ValidationError({'component':'Choose a component before publishing.'})
            if self.question_number not in [v[0] for v in COMPONENTS[self.component]['sections']]: raise ValidationError({'question_number':'Choose a valid theme or section.'})
            if self.part not in ('a','b','c','d'): raise ValidationError({'part':'Classify the question before publishing.'})
            if self.source_type=='official' and (self.part=='a' or not self.indicative_content.strip()): raise ValidationError('Official A belongs in Keywords; official B/C/D requires marking guidance.')
            if self.source_type=='additional' and (not self.collection_id or not self.collection.published or self.collection.permission_status!='allowed'): raise ValidationError('Additional questions need a published collection with reproduction permission confirmed.')
        if len(self.prompt)>10000 or len(self.indicative_content)>50000: raise ValidationError('Question or scheme is too long.')
    def __str__(self): return f'{self.component} · {self.question_number}({self.part}) · {self.prompt[:80]}'
    @property
    def marks(self): return {'a':2,**MARKS}.get(self.part,0)

class Keyword(models.Model):
    component = models.CharField(max_length=50, choices=COMPONENT_CHOICES, db_index=True)
    pool = models.CharField(max_length=80, help_text='Use the existing topic pool; beliefs and practices share a pool within each religion.')
    term = models.CharField(max_length=150)
    definition = models.TextField()
    source_url = models.URLField(blank=True)
    source_page = models.PositiveSmallIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ['component','pool','term']
        constraints = [models.UniqueConstraint(fields=['component','pool','term'],name='unique_keyword_per_pool')]
    def clean(self):
        pools = [s[2] for s in COMPONENTS.get(self.component,{}).get('sections',[])]
        if self.pool not in pools: raise ValidationError({'pool':'Use an existing keyword pool for this component.'})
        if not self.term.strip() or not self.definition.strip(): raise ValidationError('Term and definition are required.')
    def __str__(self): return self.term

class ImportLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=150)
    count = models.PositiveIntegerField()
    filename = models.CharField(max_length=200)
    def __str__(self): return f'{self.created_at:%Y-%m-%d %H:%M} · {self.count} questions · {self.actor}'

class SiteContent(models.Model):
    BLOCKS = [('home_intro','Homepage introduction'),('home_extra','Homepage additional content'),('about','About & privacy page'),('footer','Website footer')]
    key = models.CharField(max_length=30, choices=BLOCKS, unique=True)
    body = models.TextField(blank=True, max_length=50000, help_text='Use the visual editor. Changes appear on the website when you save.')
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'website content'
        verbose_name_plural = 'Website content (visual editor)'
    def save(self, *args, **kwargs):
        from .content import clean_content
        self.body = clean_content(self.body)
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values_list('body',flat=True).first()
            if previous is not None and previous != self.body: ContentRevision.objects.create(content=self,body=previous)
        super().save(*args, **kwargs)
    def __str__(self): return self.get_key_display()

class Announcement(models.Model):
    site = models.CharField(max_length=10, choices=[('re','ReRevi'),('english','EngRevi'),('history','HiRevi')], default='re', db_index=True, editable=False)
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=10000)
    published = models.BooleanField(default=False, help_text='Show this announcement at the top of the website during its scheduled dates.')
    starts_at = models.DateTimeField(null=True, blank=True, help_text='Optional; leave blank to start immediately.')
    ends_at = models.DateTimeField(null=True, blank=True, help_text='Optional; leave blank to keep showing it.')
    position = models.PositiveSmallIntegerField(default=0, help_text='Lower numbers appear first.')
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['position','-updated_at']
    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at':'End must be after start.'})
    def save(self, *args, **kwargs):
        from .content import clean_content
        self.body = clean_content(self.body)
        super().save(*args, **kwargs)
    def __str__(self): return self.title

class Feedback(models.Model):
    CATEGORIES = [('suggestion','Suggestion'),('problem','Website problem'),('content','Question or marking correction'),('other','Other')]
    STATUSES = [('new','New'),('reviewing','Reviewing'),('resolved','Resolved')]
    question = models.ForeignKey(Question,null=True,blank=True,on_delete=models.SET_NULL)
    question_reference = models.CharField(max_length=300,blank=True)
    priority = models.CharField(max_length=10,choices=[('normal','Normal'),('high','High'),('urgent','Urgent')],default='normal')
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True, help_text='Optional reply address supplied by the sender.')
    email_updates = models.BooleanField(default=False,help_text='Sender consent for an acknowledgement and feedback status updates.')
    category = models.CharField(max_length=20, choices=CATEGORIES)
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='new', db_index=True)
    admin_notes = models.TextField(blank=True, max_length=10000, help_text='Internal notes; not shown to the sender.')
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Feedback'
    def __str__(self): return self.subject


class AdminNotification(models.Model):
    feedback = models.OneToOneField(Feedback,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False,db_index=True)
    emailed_at = models.DateTimeField(null=True,blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=250,blank=True)
    next_attempt = models.DateTimeField(null=True,blank=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return 'Report #'+str(self.feedback_id)

class ContentRevision(models.Model):
    content = models.ForeignKey(SiteContent,on_delete=models.CASCADE,related_name='revisions')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return str(self.content)+' · '+str(self.created_at)

class UpdatePost(models.Model):
    site = models.CharField(max_length=10, choices=[('re','ReRevi'),('english','EngRevi'),('history','HiRevi')], default='re', db_index=True, editable=False)
    kind = models.CharField(max_length=20,choices=[('issue','Known issue'),('change','Changelog')])
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=10000)
    published = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def save(self,*args,**kwargs):
        from .content import clean_content
        self.body = clean_content(self.body)
        super().save(*args,**kwargs)
    def __str__(self): return self.title

class QuestionRevision(models.Model):
    question = models.ForeignKey(Question,on_delete=models.CASCADE,related_name='revisions')
    previous = models.JSONField()
    reason = models.CharField(max_length=500,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return str(self.question_id)+' · '+str(self.created_at)

class Article(models.Model):
    site = models.CharField(max_length=10, choices=[('re','ReRevi'),('english','EngRevi'),('history','HiRevi')], default='re', db_index=True, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=180,unique=True,help_text='The article address. Keep this unchanged after sharing the link.')
    summary = models.CharField(max_length=300,blank=True)
    body_format = models.CharField(max_length=10,choices=[('markdown','Markdown'),('html','Visual editor (existing HTML)')],default='markdown',help_text='Use Markdown for new blog posts. Existing visual posts can keep their HTML format.')
    body = models.TextField(max_length=50000)
    published = models.BooleanField(default=False,help_text='Drafts are visible only through the admin preview.')
    publish_at = models.DateTimeField(null=True,blank=True,help_text='Optional publication time (Europe/London). Enable Published to schedule; leave blank to publish immediately.')
    show_in_sidebar = models.BooleanField(default=True,help_text='Show a link in the sidebar when published.')
    position = models.PositiveSmallIntegerField(default=0,help_text='Lower numbers appear first.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['position','title']
    def save(self,*args,**kwargs):
        from .content import clean_content
        if self.body_format=='html':self.body=clean_content(self.body)
        super().save(*args,**kwargs)
    @classmethod
    def visible(cls,now=None):
        from django.utils import timezone
        return cls.objects.filter(published=True).filter(models.Q(publish_at__isnull=True)|models.Q(publish_at__lte=now or timezone.now()))
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('article_detail',args=[self.slug])
    def __str__(self): return self.title

class FAQ(models.Model):
    site = models.CharField(max_length=10, choices=[('re','ReRevi'),('english','EngRevi'),('history','HiRevi')], default='re', db_index=True, editable=False)
    question = models.CharField(max_length=250)
    answer = models.TextField(max_length=20000)
    category = models.CharField(max_length=80,default='Getting started',help_text='Group related questions under the same category name.')
    position = models.PositiveSmallIntegerField(default=0,help_text='Lower numbers appear first within the category.')
    published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['category','position','question']
        verbose_name='FAQ'
        verbose_name_plural='FAQs'
    def save(self,*args,**kwargs):
        from .content import clean_content
        self.answer=clean_content(self.answer)
        self.category=self.category.strip() or 'Getting started'
        super().save(*args,**kwargs)
    def __str__(self):return self.question
