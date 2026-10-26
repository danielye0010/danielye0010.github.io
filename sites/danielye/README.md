# danielye.net

Daniel Ye's homepage. Built with Astro, TypeScript, and Tailwind CSS; deployed on GitHub Pages by
[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) on every push to `master` that touches this folder.

## Editing content

| What | Where |
| --- | --- |
| Section text (research, engineering, projects, creative), both languages | [`src/data/portfolio.json`](src/data/portfolio.json) |
| "About Me" on the homepage | [`src/content/about-en.md`](src/content/about-en.md), [`src/content/about-zh.md`](src/content/about-zh.md) |
| Name, position, affiliation, header strings per language | [`src/data/i18n.yaml`](src/data/i18n.yaml) |
| Page titles, descriptions, keywords; links and contact details | [`src/lib/site.ts`](src/lib/site.ts) |
| Structured data (schema.org JSON-LD) | [`src/lib/structured-data.ts`](src/lib/structured-data.ts) |
| Images, project and paper subpages, `llms.txt`, `sitemap.xml`, `robots.txt` | [`public/`](public/) (served as-is) |

The build validates `portfolio.json` and `i18n.yaml` against the schemas in `src/lib/site.ts`, so a
missing or misspelled field fails the build instead of leaving a blank on the page.
After content changes, update `<lastmod>` in `public/sitemap.xml`.

Do not delete `public/CNAME`, `public/google832a9f381c11f45f.html` (Search Console) or
`public/d48e99ff3f3e2223b56b1152af5fe7c8.txt` (IndexNow key).

| Path | Purpose |
| --- | --- |
| `src/pages/[...path].astro` | The ten section pages (5 sections × English/Chinese) |
| `src/layouts/Home.astro` | Shared layout: head tags, header, language switch, dark mode |
| `src/components/PortfolioContent.astro` | Body of each section |
| `src/pages/manufacturing.astro`, `src/pages/xiaoliang/` | Redirect pages for old URLs |
| `src/styles/` | `minimal-light.scss`, `publications.css`, `portfolio.css`, and `global.css` (Tailwind setup and color tokens) |
| `scripts/check.mjs` | Post-build checks: required files, sitemap pages and canonicals, broken links, valid JSON-LD |

## Commands

Requires Node.js 22.23.4 or newer (the deploy uses Node 24).

```bash
npm ci
npm run dev       # local server with live reload
npm run build     # type check + build + checks, output in dist/
```
