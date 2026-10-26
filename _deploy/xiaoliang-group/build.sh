#!/usr/bin/env bash
# Cloudflare Pages build for https://xiaoliang.group/.
#
# Cloudflare Pages settings (unchanged): root directory = _deploy/xiaoliang-group,
# build command = bash build.sh, output directory = dist. Node version comes from .node-version.
#
# The site's source is sites/xiaoliang/ (Astro + TypeScript + Tailwind CSS). This script builds it
# there (type check, build, post-build checks; any failure stops the deploy) and copies the
# output into this folder's dist/. It reads nothing else in the repo, so danielye.net is unaffected.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$HERE/../../sites/xiaoliang" && pwd)"

echo "Node: $(node -v)"
cd "$SRC"
npm ci --no-audit --no-fund
npm run build

rm -rf "$HERE/dist"
cp -R "$SRC/dist" "$HERE/dist"
echo "Built $(find "$HERE/dist" -type f | wc -l | tr -d ' ') files into $HERE/dist"
