from types import SimpleNamespace
from django.test import SimpleTestCase
from practice.content import clean_article_html, render_article

class ArticleImageTests(SimpleTestCase):
    def test_markdown_local_screenshot_with_accessible_description(self):
        article=SimpleNamespace(body_format='markdown',body='![Choose a practice type](/static/guides/randomiser-choose.png)')
        html=render_article(article)
        self.assertIn('src="/static/guides/randomiser-choose.png"',html)
        self.assertIn('alt="Choose a practice type"',html)
        self.assertIn('loading="lazy"',html)

    def test_images_cannot_embed_remote_content_or_script_attributes(self):
        for src in ['https://example.com/track.png','//example.com/track.png','javascript:alert(1)','data:image/png;base64,AA','/static/../private.png','/static/fake.html']:
            with self.subTest(src=src):
                self.assertNotIn('<img',clean_article_html(f'<img src="{src}" onerror="alert(1)">'))
        html=clean_article_html('<img src="/static/guides/safe.png" alt="&quot; onload=&quot;bad" onerror="alert(1)" style="display:none">')
        self.assertNotIn('onerror=',html)
        self.assertNotIn('style=',html)
        self.assertIn('alt="&quot; onload=&quot;bad"',html)
