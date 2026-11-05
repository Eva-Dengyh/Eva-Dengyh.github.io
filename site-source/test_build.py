import importlib.util
import json
import tempfile
import re
import xml.etree.ElementTree as ET
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent

class Links(HTMLParser):
    def __init__(self, source):
        super().__init__(); self.urls = []; self.feed(source)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href', '').startswith('/'):
            self.urls.append(attrs['href'].split('#')[0].split('?')[0])

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('build', ROOT / 'build.py')
        cls.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.build)
        cls.pages = json.loads((ROOT / 'content.json').read_text())
        cls.folder = tempfile.TemporaryDirectory()
        cls.output = Path(cls.folder.name)
        cls.build.build(cls.output, cls.pages)
    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()
    def test_every_original_body_is_preserved_at_its_route(self):
        for page in self.pages:
            html = (self.output / page['path'].strip('/') / 'index.html').read_text()
            clean = re.sub(r'<span class="heading-anchor" id="section-\d+"></span>', '', html)
            self.assertIn(page['html'], clean, page['path'])
    def test_internal_navigation_resolves(self):
        for file in self.output.rglob('*.html'):
            for url in Links(file.read_text()).urls:
                if url:
                    target = self.output / url.strip('/')
                    self.assertTrue(target.exists() or (target / 'index.html').exists(), (file, url))
    def test_all_articles_have_paired_language_routes(self):
        posts = {locale: {page['id']: page for page in self.pages
                         if page['kind'] == 'post' and page['locale'] == locale}
                 for locale in ['zh', 'en']}
        self.assertEqual(set(posts['zh']), set(posts['en']))
        self.assertEqual(len(posts['en']), 50)
        for article_id, chinese in posts['zh'].items():
            english = posts['en'][article_id]
            self.assertEqual(chinese['date'], english['date'])
            for page, counterpart in [(chinese, english), (english, chinese)]:
                rendered = (self.output / page['path'].strip('/') / 'index.html').read_text()
                self.assertIn(f'href="{counterpart["path"]}"', rendered)
                self.assertNotIn('class="unavailable"', rendered)
    def test_metadata_and_no_client_render_requirement(self):
        for file in self.output.rglob('*.html'):
            html = file.read_text()
            self.assertIn('<main', html)
            self.assertEqual(html.count('name="description"'), 1)
            self.assertEqual(html.count('rel="canonical"'), 1)
            self.assertNotIn('__NEXT_DATA__', html)
    def test_home_introduces_the_author_and_keeps_content_navigation(self):
        for locale in ['zh','en']:
            html = (self.output / locale / 'index.html').read_text()
            about = next(page for page in self.pages
                         if page['locale'] == locale and page['kind'] == 'about')
            self.assertIn(about['html'], html)
            self.assertNotIn('data-listing', html)
            self.assertIn(f'href="/{locale}/posts/"', html)
            self.assertIn(f'href="/{locale}/projects/"', html)
            self.assertIn('hreflang="en"', html)
            self.assertIn('hreflang="zh-CN"', html)
        self.assertIn(next(page['html'] for page in self.pages
                           if page['locale'] == 'en' and page['kind'] == 'about'),
                      (self.output / 'index.html').read_text())
    def test_feed_preserves_publication_dates(self):
        feed = ET.parse(self.output / 'rss.xml')
        items = feed.findall('./channel/item')
        self.assertEqual(len(items), 50)
        self.assertEqual(items[0].findtext('pubDate'), 'Fri, 09 Oct 2026 00:00:00 GMT')
    def test_recent_article_links_are_in_date_order(self):
        html = (self.output / 'zh/posts/b2044db9-e74c-4719-b0f7-a62b8062b5d5/index.html').read_text()
        related = html.split('<section class="related">')[1]
        dates = re.findall(r'<time datetime="([^"]+)"', related)
        self.assertEqual(dates, ['2026-10-09', '2026-09-15'])
    def test_topic_classification(self):
        self.assertEqual(self.build.topic('RAG 实战'), 'ai')
        self.assertEqual(self.build.topic('Ubuntu Redis'), 'backend')
        self.assertEqual(self.build.topic('FastSAM-Demo'), 'vision')
        self.assertEqual(self.build.topic('GitHub README'), 'tools')

if __name__ == '__main__': unittest.main()
