# xiaoliang.group build

Builds Xiao Liang's pages as a standalone site for https://xiaoliang.group, deployed by
Cloudflare Pages. danielye.net (GitHub Pages) does not use anything in this folder; Jekyll
skips folders whose names start with `_`.

Content is edited in the usual places and both sites pick it up:
`xiaoliang/`, `_layouts/xl.html`, `_data/xl.yml`, `_includes/xl/`.

| File | Purpose |
|---|---|
| `build.sh` | Copies only Xiao's sources into a temp Jekyll site, builds with `xl_standalone: true`, moves the `/xiaoliang/` output to the root of `dist/`, runs `check.rb` |
| `check.rb` | Fails the build on missing files, broken root-relative links, leftover `/xiaoliang/` or `danielye.net` references, or wrong canonical URLs |
| `_config.yml` | `url: https://xiaoliang.group`, `xl_standalone: true` |
| `site/` | Pages only on the new domain: `404.html`, `robots.txt`, `sitemap.xml` |
| `static/_redirects` | 301s from old `/xiaoliang/...` paths to the root |
| `Gemfile`, `Gemfile.lock`, `.ruby-version` | Jekyll 3.10.0 / Liquid 4.0.4 (same as GitHub Pages), Ruby 3.4.4 |

## Cloudflare Pages settings

- Production branch: `master`
- Root directory: `_deploy/xiaoliang-group`
- Build command: `bash build.sh`
- Build output directory: `dist`
- Build watch paths (include): `xiaoliang/*`, `_layouts/xl.html`, `_data/xl.yml`, `_includes/xl/*`, `_deploy/xiaoliang-group/*`

## Local build

```bash
cd _deploy/xiaoliang-group
bash build.sh             # output in dist/
npx wrangler pages dev dist   # optional: serve with Cloudflare's routing rules
```
