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
    def test_untranslated_article_does_not_link_to_missing_translation(self):
        html = (self.output / 'zh/posts/ai-agent-notes-2026-03-17/index.html').read_text()
        self.assertNotIn('/en/posts/ai-agent-notes-2026-03-17/', html)
        self.assertIn('尚无英文译文', html)
    def test_metadata_and_no_client_render_requirement(self):
        for file in self.output.rglob('*.html'):
            html = file.read_text()
            self.assertIn('<main', html)
            self.assertEqual(html.count('name="description"'), 1)
            self.assertEqual(html.count('rel="canonical"'), 1)
            self.assertNotIn('__NEXT_DATA__', html)
    def test_home_lists_real_articles_and_bilingual_routes(self):
        for locale in ['zh','en']:
            html = (self.output / locale / 'index.html').read_text()
            self.assertIn('FastSAM-Demo', html)
            self.assertIn('hreflang="en"', html)
            self.assertIn('hreflang="zh-CN"', html)
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
