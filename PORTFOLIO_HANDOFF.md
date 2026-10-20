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
- 128 internal page/asset/fragment references pass: `_portfolio_dev/link-check.json`.
- All eight routes rendered at 1440 and 390 pixels, with no overflow, missing images, or missing alt text. Dark-mode persistence passes: `_portfolio_dev/visual-check.json`.
- 18 refreshed screenshots: `_portfolio_dev/screenshots/`; desktop/mobile EN/ZH pages plus dark Home.
- Gallery proof: `_portfolio_dev/gallery-proof.jpg`.
- Xiaoliang comparison: ten files unchanged except normalized build timestamps; `_portfolio_dev/regression-check.json`.
- Protected-path and photo provenance checks: `_portfolio_dev/scope-check.json`. `git diff --check` passes.
- Earlier iteration also passed keyboard navigation/theme checks and a `/preview` base-URL build; these were not rerun after the latest content-only expansion.

No edits to Xiaoliang, deployment workflows, DNS, CNAME, analytics, redirects, or shared Sass. Browser QA suppresses telemetry requests without changing production configuration. Safari/Firefox and a full accessibility audit were not performed.

## Next review

Review the local presentation and final bilingual copy. Real VR/app screenshots can replace workflow illustrations when available. The owner approved this version for publication on 2026-10-19. The sitemap now includes all eight bilingual routes. Development screenshots, logs and provenance JSON stay local and are ignored by Git; reusable check scripts remain in the source, excluded from the generated site. Publication uses the existing master branch without changes to Pages configuration, DNS, analytics, or IndexNow.

## Manufacturing organization update

The green FDM model is labeled Tiger Hill Pagoda, Suzhou / 苏州虎丘塔 following owner identification. The updated bilingual pages passed the Jekyll build, all 156 local links, and desktop/mobile checks across all eight routes with no overflow or missing images.

LPBF, DED and FDM now form one equal-weight Additive Manufacturing group. FDM modeling/printing details follow, then the compact machining/metrology gallery. Added the supplied ZEISS DuraMax CMM and HAAS CNC photos; labeled the original scanner Creaform and listed Artec Spider experience following owner confirmation. Equipment images are capped at 200px desktop / 220px mobile. Descriptions emphasize operation and capability with concise bilingual wording. Source photos are resized/re-encoded without generative changes. This update follows the existing authorized publication workflow.

## Selected projects and media refinement

Home now renders only the existing About Me content, with other sections reached through navigation. Manufacturing and project media use matching 200px desktop / 220px mobile frames; the pagoda no longer expands vertically. Selected Projects retains four distinct capabilities: AI-agent product engineering (TradeAgent), spatial interaction (VR), topology-informed 3D learning, and distributed scientific computing (~2.5 million spectra). The practice takeout application and survey dashboard were removed from the selection; More links to the GitHub repository list.

TradeAgent links directly to https://danielye0010.github.io/TradeAgent/ and uses a real screenshot of its public website hero captured on 2026-10-19. VR uses the owner-supplied screenshot unchanged. Copy was checked against the public project READMEs. No performance claims were added. Build and 128 internal references passed; all eight routes passed 1440px/390px image, overflow, and dark-theme checks.

## 2026-10-20 content simplification

Removed the separate FDM design-to-print section and Artec Spider sentence in both languages. FDM remains alongside LPBF and DED, with its card identifying the personally modeled and printed Tiger Hill Pagoda. Manufacturing introduction now identifies the owner's hands-on fabrication/measurement work and the photos as coming from those sessions. TradeAgent copy now leads with what the owner built: research agents, automated execution, dashboard, and public decision record. Build and all 124 internal links pass. The preview server needed restarting; the final bilingual manufacturing/projects pages pass image loading and overflow checks at 1440px and 390px.

Latest copy adjustment: manufacturing and TradeAgent use concise capability/action phrasing without first-person openings, matching the other cards. Contribution is conveyed by Developed, original modeling, and hands-on practice.

Project stack refinement: removed the Team project label from the portfolio and added four concise technical tags beneath each description in both locales. Tags were checked against the public READMEs and TradeAgent architecture/package metadata: MCP/LLM orchestration/SQLite/systemd; Unity/OpenXR/intent scoring/adaptive selection; PyTorch/GUDHI/persistent homology/PointNet; HTCondor/FITSio/template matching/distributed reduction.

Latest refinement: three technology labels per project, rendered as a single noninteractive tab-style strip. Replaced the list markup to avoid bullet fallback and added a build-version query to the portfolio stylesheet to refresh cached CSS. No separate Skills section was added; that part of the request is advice only.

Latest owner edit: renamed the project heading Fun Projects / 趣味项目 and moved More on GitHub directly under it. Restored the pre-redesign About Me research wording from 7a9509c^ in both languages, retaining the current paragraph separation and adding bold emphasis to the original core motivation. Affiliation and other biography paragraphs remain as before.

## Engineering page — 2026-10-20

Replaced the Manufacturing navigation/page with Engineering at `/engineering/` and `/zh/engineering/`. The old Manufacturing routes redirect to the matching Engineering route and retain hash/query context. Sitemap and bilingual canonical/alternate navigation now use Engineering. The top-level structure is Simulation & Design (CFD, FEA, CAD) followed by Manufacturing & Metrology (LPBF/DED/FDM, then ZEISS/HAAS/Creaform). Existing owner-provided photographs and compact media sizes remain.

New external method demos: forced-convection heat-sink temperature/flow by Isofilm (CC BY-SA 3.0) and truss-bridge eigenmodes by Ajay B Harish (CC BY-SA 4.0). Sources, license links, and method-demo captions are visible on both pages; `assets/img/engineering/CREDITS.txt` records transcoding and attribution. The clips are reference media, not owner simulation outputs. No solver brand or unverified result is attributed to the owner. CAD uses an explicitly labeled code-authored parametric bracket schematic. The GIFs were converted to MP4 with Tecplot-bundled ffmpeg; no generative media changes. Both clips have mute/loop/playback controls, posters, and reduced-motion handling.

Validation: Jekyll build and all 138 local references passed, including the published media-credit file. All eight canonical routes passed desktop/mobile rendering, image and alt checks, and dark-theme persistence. `_portfolio_dev/engineering-check.cjs` additionally verifies 3 simulation cards + 6 workshop cards, consistent media heights, video decode/playback, both legacy redirects with fragment retention, reduced-motion pause, and EN/ZH layouts at 1440/701/390/320px. Mobile browsers may defer offscreen autoplay; scroll-to-view playback was verified. `_portfolio_dev/engineering-check.json` is the local result. Development media originals remain only in ignored screenshots storage.

## Structure-aligned compensation paper website — 2026-10-20

Added a standalone English paper page at `/papers/structure-aligned-compensation/`, with Website links on both Research locales and a sitemap entry. Source is `papers/structure-aligned-compensation/index.html`; isolated CSS, JS, six extracted figures, original open-access PDF, citation and figure credits are in `assets/papers/structure-aligned-compensation/`. The PDF is byte-identical to the owner-supplied published article; page 1 states CC BY 4.0. Figures are cropped/re-encoded without scientific modifications. Tables 3/4 and the Table 5 roughness metric are transcribed with units and distinct numerical-validation context. No invented results or synthetic simulation visuals.

The current remote master (`ffa8f17`) was fast-forwarded before editing, preserving the newer Engineering/Projects changes. Site hosting remains the existing master-root GitHub Pages configuration and domain. No DNS/workflow changes.

Validation: Jekyll build; existing 138-link portfolio check; `python3 _portfolio_dev/check-warpage.py`; JS syntax and Git whitespace checks. Browser QA through the in-app browser verified result-tab switching, left-arrow keyboard selection, figure dialog and close, and clipboard success. A temporary iframe harness checked widths 320, 390, 768, 1440 with no document overflow, missing images, or missing alt text. Actual mobile devices/Safari/Firefox were not tested. The harness is not tracked and is removed by the final Jekyll build. Extracted text and crop manifest stay local under `_portfolio_dev/`; source PDF is the evidence for claims and displayed numbers.

### Owner-directed concise revision
Reduced the paper page to a hero, one core-idea section, and one key-results section. Three figures remain visible; only plate RMS and bracket peak residual comparisons are highlighted, with distinct labels and table references. Removed derivation, full tables, tabs, extended robustness/limitations sections and repeated resource descriptions. BibTeX is collapsed by default. Final concise build passes 23 paper references, four transcribed values, and 138 portfolio links. Earlier responsive checks describe the expanded version; concise version uses the same responsive styles with a new compact result grid.

## Paper presentation refresh — 2026-10-20

Owner requested a stronger launch-style paper presentation while retaining the concise content. Replaced the isolated paper stylesheet with a dark hero, lavender title, lime primary action, fine backdrop grid, a lit stage for the original paper figure, and large result panels. Two paper comparisons are shown as rounded reductions: plate residual RMS (0.014 to 0.0061 mm, approximately 56%) and bracket maximum residual (2.94 to 2.07 mm, approximately 30%), relative to direct inversion under the paper's simulated single-pass closed-loop evaluation. No scientific image was generated or changed. Retains three figures and two substantive sections, with reduced-motion handling, keyboard focus, image dialogs and collapsed citation.

Research entry now orders Website / Paper / Code and links the title to the paper website. Projects uses Software & Systems / 软件与系统. The separate public code repository at `../modal-based-geometric-compensation/` has a focused README update with the published title, authors, linked preview, Website-first resources and BibTeX; existing input requirements and scripts remain unchanged. Repository About gains the paper website URL.

Local Jekyll build, paper-link/metric/Website-order checks, 140 portfolio links, JS syntax and whitespace checks pass. Browser use is currently disabled in Work settings, so this visual refresh could not be rendered or screenshot-tested in this turn; the earlier version's visual results do not validate the new styling. Local build logs: `_portfolio_dev/launch-build.log`; release checks are saved locally in `_portfolio_dev/launch-release.json`.
