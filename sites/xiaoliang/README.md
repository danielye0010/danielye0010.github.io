# xiaoliang.group

Xiao Liang's homepage. Built with Astro, TypeScript, and Tailwind CSS; deployed on Cloudflare Pages
(see [`_deploy/xiaoliang-group/`](../../_deploy/xiaoliang-group/)).

## Editing content

Almost everything is in [`src/data/profile.yaml`](src/data/profile.yaml): bio fields, links, papers,
BibTeX, education, and the Chinese translations. The "About" paragraphs are in
[`src/pages/index.astro`](src/pages/index.astro) and [`src/pages/zh/index.astro`](src/pages/zh/index.astro).
The build validates `profile.yaml` against the schema in [`src/lib/profile.ts`](src/lib/profile.ts),
so a typo in a field name fails the build instead of leaving a blank on the page.

| Path | Purpose |
|---|---|
| `src/layouts/Profile.astro` | Page layout, SEO tags, structured data |
| `src/lib/structured-data.ts` | schema.org JSON-LD (Person, ProfilePage, ScholarlyArticle) |
| `src/scripts/xl.ts` | Dark-mode toggle, gradient-descent playground, BibTeX copy |
| `src/styles/` | `xl.css` (site styles) and `global.css` (Tailwind setup and color tokens) |
| `src/pages/llms.txt.ts`, `sitemap.xml.ts`, `robots.txt.ts` | Generated text files |
| `public/` | Images, icons, Cloudflare `_redirects` |
| `scripts/check.mjs` | Post-build checks: required files, broken links, canonical URLs, valid JSON-LD |

## Commands

Requires Node.js 22.23.4 or newer (Cloudflare uses Node 24).

```bash
npm ci
npm run dev       # local server with live reload
npm run build     # type check + build + checks, output in dist/
```
