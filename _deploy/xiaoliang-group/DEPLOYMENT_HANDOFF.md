# Deployment handoff: xiaoliang.group

Status as of 2026-10-16. Branch `xiaoliang-group`, PR into `master` (not merged).

| Item | Status |
|---|---|
| Standalone build, local + emulated Cloudflare Pages | Done, all checks pass |
| danielye.net regression check | Done, output byte-identical |
| Cloudflare Pages project + pages.dev preview | **Needs you** (Cloudflare sign-in) |
| Merge to `master` (enables auto-deploy) | **Needs you**, after preview check |
| xiaoliang.group DNS move to Cloudflare | **Needs you + confirmation** (email is live on this domain) |
| Live verification of https://xiaoliang.group | Pending the steps above |

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
| Project name | `xiaoliang-group` |
| Production branch | `master` |
| Framework preset | None |
| Root directory | `_deploy/xiaoliang-group` |
| Build command | `bash build.sh` |
| Build output directory | `dist` |
| Build watch paths (include) | `xiaoliang/*`, `_layouts/xl.html`, `_data/xl.yml`, `_includes/xl/*`, `_deploy/xiaoliang-group/*` |

## 3. Build and validation results

- Build: Ruby 3.3.6 and Ruby 3.4.4 (Cloudflare's default) both succeed from a clean gem cache; identical output; `check.rb` OK.
- Routing (Wrangler's local Pages emulator): `/`, `/zh/` → 200; `/zh` → 308 `/zh/`; assets, `llms.txt`, `robots.txt`, `sitemap.xml` → 200; unknown path → 404 page; `/xiaoliang/`, `/xiaoliang/zh/` → 301 to `/`, `/zh/`.
- Browser (Chromium, 1366×900 and 390×844 mobile, EN and ZH): avatar and CSS load, 4 paper cards with SVG thumbnails, landscape canvas draws and animates on click, theme toggle, BibTeX expand, language switch `/` ↔ `/zh/`; no console errors, no failed or 4xx requests, no horizontal overflow.
- Visual parity: full-page screenshots of the new build vs. live danielye.net/xiaoliang/ are pixel-identical (0 differing pixels) for all four page/viewport combinations.
- Metadata: canonical, hreflang (en, zh-Hans, x-default), og:url, og:image, twitter:image, JSON-LD `@id`/`url`/`image`/`logo`, `llms.txt`, and sitemap all use `https://xiaoliang.group/...`.

Not yet verified (needs the steps below): the real Cloudflare build, the pages.dev URL, HTTPS on the custom domain, and the live site.

## 4. Production URLs and status

- https://danielye.net/ and https://danielye.net/xiaoliang/: unchanged, live.
- https://xiaoliang-group.pages.dev/: not created yet (step A).
- https://xiaoliang.group/, https://xiaoliang.group/zh/: not live yet (step C). The apex currently has no A record.

## 5. Manual steps still required

### A. Create the Cloudflare Pages project (about 5 minutes)

1. Sign in at https://dash.cloudflare.com (the account you use for danielye.net's Web Analytics is fine).
2. **Workers & Pages → Create → Pages → Connect to Git → GitHub**. If asked to install or configure the Cloudflare Pages GitHub app, choose **Only select repositories → danielye0010.github.io**.
3. Select `danielye0010/danielye0010.github.io` and enter the settings from the table in section 2. Save and Deploy.
4. The first production build of `master` will fail with "root directory not found". That is expected until the PR is merged and does not affect anything.
5. Tell me it's connected. I'll push a commit to `xiaoliang-group` to trigger a preview build and verify `https://xiaoliang-group.xiaoliang-group.pages.dev/` over HTTP and in a browser. (Or in the project, **Deployments → Create deployment → branch `xiaoliang-group`**.)

### B. Merge the PR

After the preview checks pass, merge the PR into `master`. Cloudflare then builds production (`xiaoliang-group.pages.dev`), and every later change to Xiao's files on `master` redeploys automatically. GitHub Pages also rebuilds danielye.net; its output is unchanged.

### C. Move xiaoliang.group DNS to Cloudflare (needs your go-ahead)

Cloudflare Pages only serves an apex domain (`xiaoliang.group`, not `www.`) when the domain's DNS is on Cloudflare, so the nameservers must change. Email for this domain is hosted by Northwest (Business Identity), so every email record must be recreated exactly in Cloudflare before switching.

Current public DNS (queried 2026-10-16; nameservers `ns1/ns2.hosting.businessidentity.llc`, no DNSSEC):

| Name | Type | Value |
|---|---|---|
| `xiaoliang.group` | MX | `10 mailserver.businessidentity.llc` |
| `xiaoliang.group` | TXT | `v=spf1 a mx include:spf.postal.businessidentity.llc ~all` |
| `_dmarc` | TXT | `v=DMARC1; p=quarantine; rua=mailto:bounce@dmarc.businessidentity.llc; ruf=mailto:bounce@dmarc.businessidentity.llc; fo=1` |
| `*` (wildcard; covers `mail`, `webmail`, `smtp`, `imap`, `pop`, `autodiscover`, `autoconfig`, `www`, ...) | A | `66.223.49.89` |
| DKIM | TXT | **Unknown selector; not discoverable from outside.** Copy it from Northwest's DNS panel. |

Steps:
1. In Northwest's DNS panel for xiaoliang.group, screenshot or copy **every** record, including the DKIM `..._domainkey` TXT record and any SRV/CNAME records. Send it to me if you'd like me to check it against the list above.
2. In Cloudflare: **Add a domain → xiaoliang.group → Free plan**. Let it scan, then compare its imported records with Northwest's list and add anything missing (DKIM is the most likely gap).
3. Set every imported mail-related record to **DNS only (grey cloud)**: MX targets can't be proxied, and `mail`/`smtp`/`imap`/`pop`/`autodiscover`/`autoconfig`/`webmail` must not go through Cloudflare's proxy. The wildcard `*` record should also be DNS only.
4. Do not add an apex A record yourself; step 6 creates it.
5. At Northwest, replace the nameservers with the two Cloudflare shows you. Leave DNSSEC off. Email keeps working as long as step 2 copied all records (mail TTLs are 60 s).
6. Once Cloudflare marks the zone **Active**: Pages project → **Custom domains → Set up a domain → `xiaoliang.group`**, then again for `www.xiaoliang.group` (this replaces the `www` wildcard match, which currently points at Northwest). Cloudflare creates the records and the HTTPS certificate.
7. Tell me, and I'll verify `https://xiaoliang.group/`, `/zh/`, HTTPS, redirects, and that MX/SPF/DMARC/DKIM still resolve to the same values.

Optional, recommended: in **Bulk Redirects** (or a Redirect Rule), send `www.xiaoliang.group/*` → `https://xiaoliang.group/$1` with 301, so the site has one canonical host.

### D. After go-live: point the old pages at the new domain (your decision)

`danielye.net/xiaoliang/` still declares itself canonical, so search engines see two copies. Once xiaoliang.group is live, change `url` and `zh.url` in `_data/xl.yml` to `https://xiaoliang.group/` and `https://xiaoliang.group/zh/`, and remove the two `/xiaoliang/` entries from the root `sitemap.xml`. The old URLs keep working but point search engines to the new domain. I left this off so nothing points at a domain that doesn't resolve yet.

## 6. Rollback

- **Code**: the only shared files touched are `_layouts/xl.html` and `xiaoliang/llms.txt`. `git revert <merge commit>` on `master` restores them; danielye.net output is the same either way.
- **Cloudflare Pages**: **Deployments → (earlier deployment) → Rollback**, or delete the project. danielye.net is unaffected.
- **DNS**: set the nameservers at Northwest back to `ns1.hosting.businessidentity.llc` and `ns2.hosting.businessidentity.llc`. This process doesn't edit Northwest's records, so if Northwest keeps the zone after the nameserver change (check in their panel before switching), mail resumes as before once caches expire. The saved record list from step C.1 is the fallback.
- danielye.net's DNS, `CNAME`, and GitHub Pages settings are never touched.
