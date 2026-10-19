# Portfolio handoff — 2026-10-19

Local branch: `feat/portfolio-preview-2026-10`, based on master `21cae8a`. The owner authorized publication on 2026-10-19; this release is prepared for the existing master-based GitHub Pages deployment.

## Current presentation

Eight bilingual routes: Home, Research, Manufacturing, Projects, and their Chinese versions. About Me leads the homepage, followed by research, manufacturing, and selected software. Existing identity, biography context, contacts, language navigation, purple accent and dark-mode behavior are retained. No CV URL was present in the starting configuration.

The owner requested confident, concise capability-led writing. Research now uses **Working Papers / 研究论文（撰写中）**, with three draft topics; the published JMSE paper remains separate. Its title and six authors were verified against Crossref (`_portfolio_dev/publication-crossref.json`). No private research repositories were read.

FDM emphasizes **From 3D modeling to physical prints** and a Meshy / Hunyuan3D / Blender toolkit, without assigning a specific tool to each pictured object. The owner confirmed modeling and printing the featured work, and clarified that the ray was downloaded. The ray is removed from both rendered pages and public assets. Pagoda and bridge remain, alongside the creation → editing → print preparation → fabrication workflow.

Manufacturing also features LPBF, DED and the supplied metrology photo. The metrology asset derives from the original photograph with opaque privacy masks over credential stickers and paper text. A generative editing attempt was rejected; no generated photo is used. Source provenance remains in locally ignored `_portfolio_dev/ASSET_MANIFEST.json`, excluded from the site.

Projects span six distinct areas:
- TradeAgent — AI automation; public repository dashboard screenshot.
- Adaptive Bubble Selection VR — Unity/C#/HCI.
- Topology-Aware Point Cloud Completion — 3D learning.
- Distributed Spectral Search — HTCondor/scientific computing.
- Java Takeout System — application backend.
- Our Wisconsin Survey Explorer — R Shiny/data visualization.

The latter five use locally authored SVG workflow illustrations, labeled as illustrations rather than screenshots. Sources: `_portfolio_dev/project-visual-sources.json`. NURBSDiff was removed from the selected list to avoid overlapping geometry projects. Small team attribution remains on point-cloud completion.

## Main files

- `_data/portfolio.json`: shared bilingual content.
- `_includes/portfolio/`: page, publication, photo and project-image templates.
- `_layouts/homepage.html`: conditional personal-portfolio integration.
- `assets/css/portfolio.css`: scoped styles, including responsive image/project layouts.
- `assets/img/manufacturing/`: six current WebP assets.
- `assets/img/projects/`: dashboard screenshot and five SVG illustrations.
- `index.md`, `zh/index.md`, and six subpage stubs.

## Run locally

From WSL:

```sh
cd /mnt/c/Users/danielye/Desktop/personal/website
RUBYOPT=-r./_portfolio_dev/ruby33-logger.rb bundle exec jekyll build
python3 -m http.server 4000 --bind 127.0.0.1 --directory _site
```

Preview: http://127.0.0.1:4000/ . A loopback-only preview server was left running for review. Reuse it if port 4000 is occupied.

Ruby/Jekyll were installed in WSL; locked gems are in `/home/danielye/.cache/portfolio-gems`. The development-only Logger shim handles Jekyll 3.9.3 with Ruby 3.3. `Gemfile.lock` adds Linux platform support without upgrading pinned site dependencies.

## Validation

- Latest Jekyll build passes: `_portfolio_dev/build.log`.
- 150 internal page/asset/fragment references pass: `_portfolio_dev/link-check.json`.
- All eight routes rendered at 1440 and 390 pixels, with no overflow, missing images, or missing alt text. Dark-mode persistence passes: `_portfolio_dev/visual-check.json`.
- 18 refreshed screenshots: `_portfolio_dev/screenshots/`; desktop/mobile EN/ZH pages plus dark Home.
- Gallery proof: `_portfolio_dev/gallery-proof.jpg`.
- Xiaoliang comparison: ten files unchanged except normalized build timestamps; `_portfolio_dev/regression-check.json`.
- Protected-path and photo provenance checks: `_portfolio_dev/scope-check.json`. `git diff --check` passes.
- Earlier iteration also passed keyboard navigation/theme checks and a `/preview` base-URL build; these were not rerun after the latest content-only expansion.

No edits to Xiaoliang, deployment workflows, DNS, CNAME, analytics, redirects, or shared Sass. Browser QA suppresses telemetry requests without changing production configuration. Safari/Firefox and a full accessibility audit were not performed.

## Next review

Review the local presentation and final bilingual copy. Real VR/app screenshots can replace workflow illustrations when available. The owner approved this version for publication on 2026-10-19. The sitemap now includes all eight bilingual routes. Development screenshots, logs and provenance JSON stay local and are ignored by Git; reusable check scripts remain in the source, excluded from the generated site. Publication uses the existing master branch without changes to Pages configuration, DNS, analytics, or IndexNow.
