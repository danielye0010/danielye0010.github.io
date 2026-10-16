#!/usr/bin/env bash
# Build Xiao Liang's site as a standalone site for https://xiaoliang.group (Cloudflare Pages).
#
# Cloudflare Pages settings: root directory = _deploy/xiaoliang-group,
# build command = bash build.sh, output directory = dist.
#
# The source of truth stays in the main repo (xiaoliang/, _layouts/xl.html, _data/xl.yml,
# _includes/xl/). This script copies only those files into a scratch Jekyll site, builds it
# with xl_standalone: true, and moves the /xiaoliang/ output to the root of dist/.
# It never writes outside this folder and a temp dir, so the danielye.net build is unaffected.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/dist"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cd "$HERE"
echo "Ruby: $(ruby -v)"
bundle install --quiet

# 1. Assemble a minimal Jekyll source tree.
mkdir -p "$STAGE/_layouts" "$STAGE/_data" "$STAGE/_includes"
cp "$HERE/_config.yml"           "$STAGE/_config.yml"
cp "$REPO/_layouts/xl.html"      "$STAGE/_layouts/"
cp "$REPO/_data/xl.yml"          "$STAGE/_data/"
cp -R "$REPO/_includes/xl"       "$STAGE/_includes/"
cp -R "$REPO/xiaoliang"          "$STAGE/xiaoliang"
cp "$HERE"/site/*                "$STAGE/xiaoliang/"

# 2. Build.
JEKYLL_ENV=production bundle exec jekyll build --source "$STAGE" --destination "$STAGE/_site"

# 3. Move the /xiaoliang/ tree to the root of dist/ and add Cloudflare control files.
rm -rf "$OUT"
mkdir -p "$OUT"
cp -R "$STAGE/_site/xiaoliang/." "$OUT/"
cp "$HERE"/static/_redirects "$OUT/"

# 4. Fail the build on anything that would break on the new domain.
bundle exec ruby "$HERE/check.rb" "$OUT"
echo "Built $(find "$OUT" -type f | wc -l | tr -d ' ') files into $OUT"
