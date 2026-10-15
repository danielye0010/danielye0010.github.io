# Daniel Ye — Personal Website

Source for **[danielye.net](https://danielye.net/)**, the academic homepage of **Daniel Ye** (Yifei Ye, 叶逸飞), a Ph.D. candidate in Industrial Engineering at **Iowa State University** (Department of Industrial and Manufacturing Systems Engineering; Center for Nondestructive Evaluation), advised by Dr. Qing Li. His research focuses on modeling and correcting 3D shape deformation in additive manufacturing, with broader interests in computational geometry, geometry processing, 3D deep learning, and generative 3D.

- Website: https://danielye.net/
- Google Scholar: https://scholar.google.com/citations?user=viHpZJQAAAAJ
- LinkedIn: https://www.linkedin.com/in/danielye0001/

## Structure

| Path | Purpose |
| --- | --- |
| `index.md` | English homepage (`lang: en`, `ref: home`) |
| `zh/index.md` | Simplified Chinese homepage at `/zh/` (`lang: zh-Hans`, `ref: home`) |
| `_data/i18n.yml` | Per-language header strings (name, position, affiliation, switch label) |
| `_config.yml` | Name, affiliation, links, SEO description |
| `_layouts/homepage.html` | Page template, meta tags, JSON-LD structured data |
| `llms.txt` | Plain-text profile summary for LLM crawlers |
| `sitemap.xml`, `robots.txt` | Crawling and indexing (update `<lastmod>` when content changes) |
| `d48e99ff3f3e2223b56b1152af5fe7c8.txt` | IndexNow key (do not delete) |
| `.github/workflows/indexnow.yml` | Pings IndexNow (Bing etc.) after each GitHub Pages build |
| `xiaoliang/`, `_layouts/xl.html`, `_data/xl.yml` | Separate homepage for Xiao Liang at `/xiaoliang/` |

To add a translated page, give it the same `ref` as its counterpart and a `lang` key that exists in `_data/i18n.yml`; the layout adds `hreflang` links and the language switch automatically.

Deployed automatically by GitHub Pages (Jekyll). Local preview:

```bash
bundle install
bundle exec jekyll serve
```

## Acknowledgements

Built on Yaoyao Liu's [minimal-light](https://github.com/yaoyao-liu/minimal-light) theme (CC0 1.0), which derives from [pages-themes/minimal](https://github.com/pages-themes/minimal) and [orderedlist/minimal](https://github.com/orderedlist/minimal).
