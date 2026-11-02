# Eva Lab

A bilingual personal developer blog, statically published on GitHub Pages.

## Edit and build

Requires Python 3.10+; no third-party packages.

- `site-source/content.json`: migrated original articles, projects and about pages. Article entries contain `locale`, `id`, `title`, `date`, `html`, `path` and `kind`.
- `site-source/site.json`: site URL, intro, GitHub profile and topic configuration.
- `site-source/build.py`: static templates, routes, feeds and metadata.
- `site-source/site.css`, `site-source/site.js`: shared presentation and progressive enhancement.

```sh
python3 site-source/build.py
python3 -m unittest discover -s site-source -p 'test_*.py'
node --check site-source/site.js
python3 -m http.server 4173 --bind 127.0.0.1
```

Open `http://127.0.0.1:4173/` for Chinese or `/en/` for English. Run the build after source changes; serve the repository root, not `site-source/`. Search and topic filters run locally, without sending visitor queries to a server. Articles remain readable without JavaScript.

To add an article, add a new entry with `kind: "post"` and a stable path such as `/zh/posts/my-note/`. For a translated version, use the same `id` under `/en/posts/my-note/`. Rebuild and verify; available translations are detected by route. Existing article URLs remain unchanged.

The build updates static HTML, `/assets/`, RSS, sitemap, robots and favicon. The old Next.js bundles, data payloads and unused fonts have been removed; the site runs entirely from the new source and generated assets. This checkout remains compatible with GitHub Pages; pushing the generated files uses the existing publication setup.
