# Deployment handoff: xiaoliang.group

> **Update 2026-10-26:** the site was rebuilt with Astro + TypeScript + Tailwind CSS in `sites/xiaoliang/`.
> `build.sh` now builds that project; the Jekyll-specific files described below (`_config.yml`, `check.rb`,
> `site/`, `static/`, Gemfile) were replaced by their Astro equivalents (`src/pages/`, `scripts/check.mjs`,
> `public/_redirects`). Cloudflare settings, domains, and DNS below are unchanged and still current.

Status as of 2026-10-18: **live**. PR #2 merged into `master`.

| Item | Status |
|---|---|
| Standalone build, local + emulated Cloudflare Pages | Done, all checks pass |
| danielye.net regression check | Done: build output byte-identical; live `/xiaoliang/` pixel-identical before vs after merge |
| Cloudflare Pages project (`danielye0010-github-io`) + preview | Done, verified |
| Merge to `master` (auto-deploy on push) | Done (PR #2) |
| xiaoliang.group DNS moved to Cloudflare | Done: nameservers `heidi.ns.cloudflare.com`, `mario.ns.cloudflare.com`; all email records copied and verified |
| Custom domains `xiaoliang.group`, `www.xiaoliang.group` | Active, HTTPS certificates issued |
| Live verification | Done (see section 4) |

## 1. Architecture and why it is safe

One repo, two independent deployments of the same source:

- **danielye.net**: GitHub Pages builds `master` as before. Nothing about its config, `CNAME`, DNS, or theme changed. `/xiaoliang/` and `/xiaoliang/zh/` keep working.
- **xiaoliang.group**: a separate Cloudflare Pages project with root directory `_deploy/xiaoliang-group`. Its `build.sh` copies only Xiao's sources (`xiaoliang/`, `_layouts/xl.html`, `_data/xl.yml`, `_includes/xl/`) into a temp Jekyll site, builds with `xl_standalone: true`, and moves the output to the domain root.

Why it can't affect danielye.net:
- The shared layout only changes behavior when `site.xl_standalone` is set, which only the Cloudflare build sets. I built danielye.net before and after the change with github-pages 232 (the gem set GitHub Pages runs): all 38 output files are identical apart from build timestamps.
- Jekyll skips folders starting with `_`, so `_deploy/` is never published on danielye.net (confirmed in the same diff).
- The Cloudflare build never writes outside its folder and a temp dir, and uses its own Gemfile, so the root `Gemfile`/`Gemfile.lock` are untouched.

## 2. Files changed and deployment configuration

Changed (output on danielye.net unchanged):
- `_layouts/xl.html`: `/xiaoliang` path prefix and `https://danielye.net` origin now come from two variables, set from `site.xl_standalone`.
- `xiaoliang/llms.txt`: same switch; the "hosted on danielye.net" sentence is omitted on the new domain.

Added, all under `_deploy/xiaoliang-group/`:
- `build.sh`, `check.rb` (build fails on missing files, broken root-relative links, leftover `/xiaoliang/` or `danielye.net` references, wrong canonical)
- `_config.yml` (`url: https://xiaoliang.group`, `xl_standalone: true`)
- `Gemfile`, `Gemfile.lock` (Jekyll 3.10.0, Liquid 4.0.4, Bundler 2.6.9), `.ruby-version` (3.4.4)
- `site/404.html`, `site/robots.txt`, `site/sitemap.xml`; `static/_redirects` (301 `/xiaoliang/*` → `/*`)
- `README.md`, this file

Cloudflare Pages settings:

| Setting | Value |
|---|---|
| Project name | `danielye0010-github-io` (auto-named by Cloudflare; only affects the pages.dev test URL) |
| Production branch | `master` |
| Framework preset | None |
| Root directory | `_deploy/xiaoliang-group` |
| Build command | `bash build.sh` |
| Build output directory | `dist` |
| Build watch paths | `*` (default: every push builds; a build takes under a minute) |

## 3. Build and validation results

- Build: Ruby 3.3.6 and Ruby 3.4.4 (Cloudflare's default) both succeed from a clean gem cache; identical output; `check.rb` OK.
- Routing (Wrangler's local Pages emulator): `/`, `/zh/` → 200; `/zh` → 308 `/zh/`; assets, `llms.txt`, `robots.txt`, `sitemap.xml` → 200; unknown path → 404 page; `/xiaoliang/`, `/xiaoliang/zh/` → 301 to `/`, `/zh/`.
- Browser (Chromium, 1366×900 and 390×844 mobile, EN and ZH): avatar and CSS load, 4 paper cards with SVG thumbnails, landscape canvas draws and animates on click, theme toggle, BibTeX expand, language switch `/` ↔ `/zh/`; no console errors, no failed or 4xx requests, no horizontal overflow.
- Visual parity: full-page screenshots of the new build vs. live danielye.net/xiaoliang/ are pixel-identical (0 differing pixels) for all four page/viewport combinations.
- Metadata: canonical, hreflang (en, zh-Hans, x-default), og:url, og:image, twitter:image, JSON-LD `@id`/`url`/`image`/`logo`, `llms.txt`, and sitemap all use `https://xiaoliang.group/...`.

The real Cloudflare preview build was then checked the same way: its files matched the local build, and the full browser test above passed on desktop and mobile. Checks on the live custom domain are in section 4.

## 4. Production URLs and status

Verified 2026-10-18 in a real browser:
- https://xiaoliang.group/: 200 over HTTPS, canonical `https://xiaoliang.group/`, avatar/CSS/JS load, 4 paper cards, landscape canvas interactive, no failed requests.
- https://xiaoliang.group/zh/: 200, `lang="zh-Hans"`, canonical `https://xiaoliang.group/zh/`; EN ↔ 中文 switch works both ways.
- http://www.xiaoliang.group/ → HTTPS, serves the same site (canonical points to the apex).
- `/xiaoliang/...` on the new domain → 301 to the root; unknown paths → 404 page; `llms.txt`, `robots.txt`, `sitemap.xml` → 200.
- Email DNS served by Cloudflare, identical to Northwest's original zone (all DNS only, not proxied):

| Name | Type | Value |
|---|---|---|
| `xiaoliang.group` | MX | `10 mailserver.businessidentity.llc` |
| `xiaoliang.group` | TXT | `v=spf1 a mx include:spf.postal.businessidentity.llc ~all` |
| `_dmarc` | TXT | `v=DMARC1; p=quarantine; rua=mailto:bounce@dmarc.businessidentity.llc; ruf=mailto:bounce@dmarc.businessidentity.llc; fo=1` |
| `postal-bhzxxj._domainkey` | TXT | `v=DKIM1; t=s; h=sha256; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDh74REvn7N8c/RSqSYiRnuCB2uvjAo0/qIq3+V6gqLPCLVCTFXbvFKpYSdPs125TKdVaUAj+FgpLMqmGsN119NDVnd6g+1ohRcsyOCnW3SETCGx+fSv2X1J+sGs5ewJUs99qy1v6z82s/cyBPE3vsogU7AGRm8SEn+S/iasxH5pwIDAQAB;` |
| `psrp` | CNAME | `rp.postal.businessidentity.llc` |
| `*` | A | `66.223.49.89` (covers `mail`, `webmail`, `smtp`, `imap`, `pop`, `autodiscover`, ...) |
| `_acme-challenge` | TXT | `DDO4MqXQSfJOUADSLXoncSUmm-7NzVNPLo6XtOf2oYo` and `z-LKqwzosy1cIEZRwSpKI9U_6426kgil6RL72CueFVM` (Northwest's certificate validation; harmless) |

  Added by Cloudflare Pages for the website: `xiaoliang.group` and `www.xiaoliang.group` (proxied, managed by the Pages custom-domain setup).
- https://danielye.net/, `/xiaoliang/`, `/xiaoliang/zh/`: 200, unchanged. danielye.net DNS untouched.
- pages.dev: https://danielye0010-github-io.pages.dev/

## 5. Remaining optional steps

- **Test email once**: send from the xiaoliang.group mailbox to an outside address and reply back. DNS is verified; whether the mailbox itself exists is set in Northwest's email service.
- **www → apex redirect** (optional): www already serves the site with the apex as canonical. To redirect instead: Cloudflare → xiaoliang.group → Rules → Redirect Rules → `www.xiaoliang.group/*` → `https://xiaoliang.group/${1}`, 301.
- **Point the old pages at the new domain** (your decision): `danielye.net/xiaoliang/` still declares itself canonical. To consolidate search ranking, set `url` and `zh.url` in `_data/xl.yml` to `https://xiaoliang.group/` and `https://xiaoliang.group/zh/`, and drop the two `/xiaoliang/` entries from the root `sitemap.xml`. Old URLs keep working.

## 6. Rollback

- **Code**: the only shared files touched are `_layouts/xl.html` and `xiaoliang/llms.txt`. `git revert <merge commit>` on `master` restores them; danielye.net output is the same either way.
- **Cloudflare Pages**: **Deployments → (earlier deployment) → Rollback**, or delete the project. danielye.net is unaffected.
- **DNS**: at Northwest (Domains → xiaoliang.group → General → Nameserver Settings), switch back to "Use our nameservers" (`ns1/ns2.hosting.businessidentity.llc`). Northwest's own DNS records were not edited and were still present when the switch was made; the complete record table in section 4 is the fallback if they need to be re-entered.
- danielye.net's DNS, `CNAME`, and GitHub Pages settings are never touched.
