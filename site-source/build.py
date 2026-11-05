"""Dependency-free static publisher. Content retains the original exported HTML."""
from pathlib import Path
from html import escape, unescape
from datetime import datetime, timezone
from email.utils import format_datetime
import json
import re
import shutil
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parent
CONFIG = json.loads((SOURCE / 'site.json').read_text())
TEXT = {
 'zh': dict(home='首页', posts='文章', projects='项目', about='关于', hello='你好，我是 Eva。', role='程序员 / AI 应用开发', latest='最近的文章', all='全部文章', topics='按主题阅读', archive='归档', intro='在这里，边做边记录。', search='搜索文章', placeholder='搜索标题、关键词…', empty='没有找到相关文章，试试其他关键词。', count='篇文章', clear='全部主题', back='返回文章列表', toc='本文目录', minute='分钟阅读', top='回到顶部 ↑', feed='RSS 订阅', note='学习、构建，持续记录。', more='查看全部项目', none='尚无英文译文', project_intro='一些把想法付诸实践的尝试。代码、工具，以及持续迭代的项目。', about_intro='关于我，以及一路走来的经历。', filter='文章筛选', result='篇匹配', excerpt='阅读这篇笔记，了解完整的实践过程。'),
 'en': dict(home='Home', posts='Writing', projects='Projects', about='About', hello='Hi, I’m Eva.', role='SOFTWARE DEVELOPER / AI APPLICATIONS', latest='Recent writing', all='All writing', topics='Explore topics', archive='Archive', intro='Learning by building. Thinking in writing.', search='Search writing', placeholder='Search titles or keywords…', empty='No matching articles. Try another keyword.', count='articles', clear='All topics', back='Back to writing', toc='On this page', minute='min read', top='Back to top ↑', feed='RSS feed (Chinese)', note='Learning, building, and taking notes.', more='All projects', none='No English translation yet', project_intro='Ideas turned into working software. Open-source tools and projects, built through practice.', about_intro='A little about me and the path so far.', filter='Filter writing', result='matches', excerpt='Read the full note for the details and practical experience.')
}

def plain(html):
    return re.sub(r'\s+', ' ', unescape(re.sub('<[^>]*>', ' ', html))).strip()

def topic(title):
    for key, item in CONFIG['topics'].items():
        if any(word in title.lower() for word in item['keywords']):
            return key
    return 'tools'

def excerpt(page):
    text = plain(page['html'])
    return text[:110].rstrip('，,。.;；') + ('…' if len(text) > 110 else '')

def destination(path):
    return path.strip('/') + '/index.html' if path != '/' else 'index.html'

def language_paths(path, available):
    if path == '/':
        return {'zh': '/', 'en': '/en/'}
    other = 'en' if path.startswith('/zh/') else 'zh'
    counterpart = re.sub(r'^/(zh|en)/', f'/{other}/', path)
    pairs = {path.split('/')[1]: path}
    if counterpart in available:
        pairs[other] = counterpart
    return pairs

def header(locale, section, pairs):
    text = TEXT[locale]
    nav_routes = [('home', f'/{locale}/'), ('posts', f'/{locale}/posts/'), ('projects', f'/{locale}/projects/')]
    active = 'home' if section == 'about' else section
    nav = ''.join(f'<a href="{route}" {"aria-current=page" if active == key else ""}>{text[key]}</a>' for key, route in nav_routes)
    languages = []
    for lang, label in [('zh','中文'),('en','EN')]:
        if lang in pairs:
            current = ' aria-current="true"' if lang == locale else ''
            languages.append(f'<a href="{pairs[lang]}" lang="{lang}"{current}>{label}</a>')
        else:
            languages.append(f'<span class="unavailable" title="{text["none"]}">{label}</span>')
    return f'''<a class="skip" href="#main">{'跳到正文' if locale == 'zh' else 'Skip to content'}</a>
    <header class="header"><a class="brand" href="/{locale}/" aria-label="Eva Lab {text['home']}"><span class="brand-mark" aria-hidden="true">e<span>.</span></span>Eva Lab<span class="brand-sub"> / notes</span></a>
    <nav aria-label="{text['home']}">{nav}</nav><div class="languages" aria-label="Language">{'<span aria-hidden="true">/</span>'.join(languages)}</div></header>'''

def shell(locale, path, title, description, body, section, available, schema=None):
    canonical_path = '/' if path == '/zh/' else path
    pairs = language_paths(canonical_path, available)
    if path == '/en/':
        pairs['zh'] = '/'
    alternates = ''.join(f'<link rel="alternate" hreflang="{"zh-CN" if lang == "zh" else "en"}" href="{CONFIG["url"]}{route}">' for lang, route in pairs.items())
    data = json.dumps(schema, ensure_ascii=False).replace('<','\\u003c') if schema else ''
    return f'''<!doctype html><html lang="{'zh-CN' if locale == 'zh' else 'en'}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · Eva Lab</title><meta name="description" content="{escape(description, quote=True)}">
<meta name="robots" content="index,follow"><meta name="theme-color" content="#fafbf9">
<link rel="canonical" href="{CONFIG['url']}{canonical_path}">{alternates}
<meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:url" content="{CONFIG['url']}{canonical_path}"><meta property="og:type" content="{'article' if schema else 'website'}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css">
<link rel="alternate" type="application/rss+xml" title="Eva Lab · 中文" href="/rss.xml">
<script src="/assets/site.js" defer></script>{'<script type="application/ld+json">'+data+'</script>' if schema else ''}</head>
<body><div class="site">{header(locale,section,pairs)}<main id="main">{body}</main>
<footer class="footer"><span>© {CONFIG['year']} Eva Lab<span class="footer-note"> · {TEXT[locale]['note']}</span></span><div><a href="{CONFIG['github']}">GitHub ↗</a><a href="/rss.xml">RSS ↗</a><a href="#main">↑ Top</a></div></footer></div></body></html>'''

def post_rows(posts, locale, limit=None):
    result = []
    for page in posts[:limit]:
        category = topic(page['title'])
        search = escape(page['title']+' '+excerpt(page)+' '+CONFIG['topics'][category][locale], quote=True)
        result.append(f'''<article class="post-row" data-post data-topic="{category}" data-year="{page['date'][:4]}" data-search="{search}">
<time datetime="{page['date']}">{page['date'].replace('-','.')}</time><div><a class="post-title" href="{page['path']}">{escape(page['title'])}</a>
<p>{escape(excerpt(page))}</p><span class="post-category">{CONFIG['topics'][category][locale]}</span></div><span class="row-arrow" aria-hidden="true">↗</span></article>''')
    return ''.join(result)

def sidebar(posts, locale):
    text = TEXT[locale]
    counts = {key: sum(topic(p['title']) == key for p in posts) for key in CONFIG['topics']}
    buttons = f'<button data-topic-filter="all" aria-pressed="true">{text["clear"]}<span>{len(posts):02}</span></button>'
    for key, count in counts.items():
        if count:
            buttons += f'<button data-topic-filter="{key}" aria-pressed="false">{CONFIG["topics"][key][locale]}<span>{count:02}</span></button>'
    years = sorted({p['date'][:4] for p in posts}, reverse=True)
    archive = ''.join(f'<a href="/{locale}/posts/?year={year}">{year}<span>↗</span></a>' for year in years)
    return f'''<aside class="sidebar"><section><h3>{text['topics']}</h3><div class="topic-list">{buttons}</div></section><section><h3>{text['archive']}</h3>{archive}</section><section class="sidebar-note"><span class="mono">README.md</span><p>{text['intro']}</p><a href="/{locale}/">{text['about']} ↗</a></section></aside>'''

def profile_home(page, locale):
    text = TEXT[locale]
    return f'''<section class="page-intro"><p class="eyebrow">ABOUT / EVA</p><h1>{text['hello']}</h1>
<div class="social"><a href="/{locale}/posts/">{text['posts']} ↗</a><a href="/{locale}/projects/">{text['projects']} ↗</a><a href="{CONFIG['github']}">GitHub ↗</a></div></section>
<div class="prose about-content">{page['html']}</div>'''

def listing(posts, locale):
    text = TEXT[locale]
    intro = f'<section class="page-intro"><p class="eyebrow">WRITING / ARCHIVE</p><h1>{text["all"]}<span class="total">{len(posts):02}</span></h1><p>{text["intro"]}</p></section>'
    search = f'''<div class="search-wrap"><label for="search" class="sr-only">{text['search']}</label><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="{text['placeholder']}" autocomplete="off"><span class="search-hint" aria-hidden="true">/</span></div>'''
    return f'''{intro}<section class="writing" data-listing data-preview-limit="0"><div class="writing-main"><div class="section-heading"><h2>{text['posts']}<span class="total">{len(posts):02}</span></h2><a href="/{locale}/posts/">{text['all']} ↗</a></div>
{search}<p id="result-count" class="result-count" aria-live="polite" data-unit="{text['result']}"></p><div class="post-list">{post_rows(posts,locale)}</div><p id="empty" hidden>{text['empty']}</p></div>{sidebar(posts,locale)}</section>'''

def article(page, locale, all_posts):
    text = TEXT[locale]
    headings = re.findall(r'<h([23])(?:\s[^>]*)?>(.*?)</h\1>', page['html'], re.S)
    toc = ''
    if headings:
        links = ''.join(f'<li><a href="#section-{index}">{escape(plain(title))}</a></li>' for index, (_, title) in enumerate(headings))
        toc = f'<aside class="toc"><h2>{text["toc"]}</h2><ol>{links}</ol><a class="back-top" href="#main">{text["top"]}</a></aside>'
    heading_index = iter(range(len(headings)))
    body = re.sub(r'<h[23](?:\s[^>]*)?>', lambda match: f'<span class="heading-anchor" id="section-{next(heading_index)}"></span>'+match[0], page['html'])
    alternate = '/en/posts/'+page['id']+'/'
    notice = f'<span class="translation-note">{text["none"]}</span>' if locale == 'zh' and not any(p['path'] == alternate for p in all_posts) else ''
    related = sorted([p for p in all_posts if p['locale']==locale and p['path']!=page['path']], key=lambda p:(p['date'],p['title']), reverse=True)[:2]
    category = CONFIG['topics'][topic(page['title'])][locale]
    minutes = max(1,round(len(plain(page['html']))/(450 if locale=='zh' else 1100)))
    return f'''<div class="article-heading"><a class="back-link" href="/{locale}/posts/">← {text['back']}</a><p class="eyebrow">{category}</p><h1>{escape(page['title'])}</h1><div class="article-meta"><span>Eva</span><span>·</span><time datetime="{page['date']}">{page['date'].replace('-','.')}</time><span>·</span><span>{minutes} {text['minute']}</span>{notice}</div></div>
<div class="article-layout"><article class="prose" data-article>{body}</article>{toc}</div><section class="related"><div class="section-heading"><h2>{text['latest']}</h2></div>{post_rows(related,locale)}</section>'''

def build(output, pages):
    output.mkdir(parents=True, exist_ok=True)
    routes = {p['path'] for p in pages} | {'/','/zh/','/en/','/zh/posts/','/en/posts/'}
    rendered = {}
    for locale in ['zh','en']:
        text = TEXT[locale]
        posts = sorted([p for p in pages if p['kind']=='post' and p['locale']==locale],key=lambda p:(p['date'],p['title']), reverse=True)
        about = next(p for p in pages if p['locale']==locale and p['kind']=='about')
        for path, home in [(f'/{locale}/',True),(f'/{locale}/posts/',False)]+([('/',True)] if locale=='zh' else []):
            body = profile_home(about, locale) if home else listing(posts, locale)
            description = excerpt(about) if home else CONFIG['intro'][locale]
            rendered[path] = shell(locale,path,text['hello'] if home else text['all'],description,body,'home' if home else 'posts',routes)
        for page in (p for p in pages if p['locale']==locale):
            if page['kind']=='post':
                body = article(page,locale,[p for p in pages if p['kind']=='post'])
                schema = {'@context':'https://schema.org','@type':'BlogPosting','headline':page['title'],'datePublished':page['date'],'author':{'@type':'Person','name':'Eva','url':CONFIG['url']+f'/{locale}/about/'},'inLanguage':locale,'mainEntityOfPage':CONFIG['url']+page['path']}
                title, description = page['title'], excerpt(page)
            else:
                title = text[page['kind']]
                description = text['project_intro' if page['kind']=='projects' else 'about_intro']
                body = f'<section class="page-intro"><p class="eyebrow">{"OPEN SOURCE / BUILDS" if page["kind"]=="projects" else "ABOUT / EVA"}</p><h1>{title}</h1><p>{description}</p></section><div class="prose {page["kind"]}-content">{page["html"]}</div>'
                schema = None
            rendered[page['path']] = shell(locale,page['path'],title,description,body,page['kind'] if page['kind']!='post' else 'posts',routes,schema)
    for path, html in rendered.items():
        file = output / destination(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(html)
    write_support_files(output, rendered, pages)
    return rendered

def write_support_files(output, rendered, pages):
    assets = output / 'assets'
    assets.mkdir(exist_ok=True)
    for name in ['site.css','site.js']:
        shutil.copyfile(SOURCE/name, assets/name)
    favicon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="9" fill="#263e53"/><text x="10" y="29" font-family="monospace" font-size="30" fill="#fff">e</text><circle cx="31" cy="29" r="2" fill="#8fb1a0"/></svg>'
    (output/'favicon.svg').write_text(favicon)
    feed = ET.Element('rss', version='2.0')
    channel = ET.SubElement(feed, 'channel')
    for key, value in [('title','Eva Lab'),('link',CONFIG['url']),('description',CONFIG['intro']['zh']),('language','zh-CN')]:
        ET.SubElement(channel,key).text = value
    ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')
    ET.SubElement(channel,'{http://www.w3.org/2005/Atom}link',href=CONFIG['url']+'/rss.xml',rel='self',type='application/rss+xml')
    for page in sorted((p for p in pages if p['kind']=='post' and p['locale']=='zh'),key=lambda p:p['date'],reverse=True):
        item = ET.SubElement(channel,'item')
        for key, value in [('title',page['title']),('link',CONFIG['url']+page['path']),('guid',CONFIG['url']+page['path']),('description',excerpt(page))]:
            ET.SubElement(item,key).text = value
        ET.SubElement(item,'pubDate').text = format_datetime(datetime.fromisoformat(page['date']).replace(tzinfo=timezone.utc),usegmt=True)
    ET.ElementTree(feed).write(output/'rss.xml',encoding='utf-8',xml_declaration=True)
    (output/'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {CONFIG["url"]}/sitemap.xml\n')
    urls = ''.join(f'<url><loc>{CONFIG["url"]}{path}</loc></url>' for path in sorted(rendered) if path!='/zh/')
    (output/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>')
    error = shell('zh','/404.html','页面未找到','页面不存在，请返回文章列表。','<section class="page-intro error"><p class="eyebrow">404 / NOT FOUND</p><h1>这一页还没有写好。</h1><p>链接可能已失效，或地址输入有误。</p><a href="/">返回首页 →</a></section>','',{'/404.html'})
    error = error.replace('name="robots" content="index,follow"', 'name="robots" content="noindex,follow"')
    (output/'404.html').write_text(error)
    (output/'404').mkdir(exist_ok=True)
    (output/'404/index.html').write_text(error)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=SOURCE.parent)
    args = parser.parse_args()
    pages = json.loads((SOURCE/'content.json').read_text())
    result = build(args.output, pages)
    print(f'Built {len(result)} content routes + 404 pages at {args.output}')
