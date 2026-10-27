"""Small HTML allowlist for locally hosted editorial content."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
from django import forms
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe

ALLOWED = {'p','br','span','div','h1','h2','h3','h4','strong','b','em','i','u','s','ul','ol','li','blockquote','a','hr'}
VOID = {'br','hr'}

def safe_link(value):
    value = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return ''
    parsed = urlsplit(value)
    if parsed.scheme.lower() in ('https','http','mailto') or (not parsed.scheme and not parsed.netloc and value.startswith(('/', '#')) and not value.startswith('//') and '\\' not in value):
        return value
    return ''

class ContentHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED: return
        attributes = ''
        if tag == 'a':
            try: href = safe_link(dict(attrs).get('href', ''))
            except ValueError: href = ''
            if href: attributes = f' href="{escape(href, quote=True)}" rel="noreferrer noopener"'
        self.parts.append(f'<{tag}{attributes}>')
        if tag not in VOID: self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag not in self.stack: return
        while self.stack:
            current = self.stack.pop()
            self.parts.append(f'</{current}>')
            if current == tag: break
    def handle_data(self, data): self.parts.append(escape(data))

def clean_content(value):
    parser = ContentHTML()
    parser.feed(value or '')
    parser.close()
    parser.parts.extend(f'</{tag}>' for tag in reversed(parser.stack))
    return ''.join(parser.parts)

class VisualEditor(forms.Textarea):
    template_name = 'widgets/visual_editor.html'
    def get_context(self, name, value, attrs):
        return super().get_context(name, clean_content(value or ''), attrs)
    class Media:
        css = {'all': ('admin/content-editor.css',)}
        js = ('admin/content-editor.js',)

def website_content(request):
    from .models import SiteContent, Announcement, Article
    from .site_scope import site_for_request
    site=site_for_request(request)
    now = timezone.now()
    blocks = {row.key: mark_safe(clean_content(row.body)) for row in SiteContent.objects.all()}
    notices = Announcement.objects.filter(published=True,site=site).filter(Q(starts_at__isnull=True)|Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True)|Q(ends_at__gt=now))
    sidebar_articles=Article.visible().filter(show_in_sidebar=True,site=site).only('title','slug')
    dashboard={}
    if request.path.startswith('/admin/') and request.user.is_staff:
        from .models import AdminNotification,Feedback,Question
        dashboard={'unread':AdminNotification.objects.filter(read=False).count() if request.user.has_perm('practice.view_adminnotification') else 0,'new_feedback':Feedback.objects.filter(status='new').count() if request.user.has_perm('practice.view_feedback') else 0,'review_questions':Question.objects.filter(status='review').count() if request.user.has_perm('practice.view_question') else 0}
    from django.conf import settings
    return {'site_name':'RE Revi','source_url':settings.SOURCE_URL,'support_email':settings.SUPPORT_EMAIL,'sidebar_articles':sidebar_articles,'admin_dashboard':dashboard,'site_content':blocks,'site_announcements':[{'title':row.title,'body':mark_safe(clean_content(row.body))} for row in notices]}


def render_article(article):
    """Convert Markdown at display time, then apply the HTML/link allowlist."""
    if article.body_format=='markdown':
        import markdown
        value=markdown.markdown(article.body or '',extensions=['extra','sane_lists'])
    else:value=article.body
    return clean_article_html(value)


def clean_article_html(value):
    class ArticleHTML(ContentHTML):
        def handle_starttag(self,tag,attrs):
            if tag in {'pre','code','table','thead','tbody','tr','th','td','del','h5','h6'}:
                self.parts.append('<'+tag+'>');self.stack.append(tag)
            else:super().handle_starttag(tag,attrs)
    parser=ArticleHTML();parser.feed(value or '');parser.close()
    parser.parts.extend('</'+tag+'>' for tag in reversed(parser.stack))
    return ''.join(parser.parts)
