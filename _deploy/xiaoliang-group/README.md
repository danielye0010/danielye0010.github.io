# xiaoliang.group build

Cloudflare Pages entry point for https://xiaoliang.group. The site itself lives in
[`sites/xiaoliang/`](../../sites/xiaoliang/) (Astro + TypeScript + Tailwind CSS).
danielye.net (GitHub Pages) does not use anything in this folder.

| File | Purpose |
|---|---|
| `build.sh` | Installs and builds `sites/xiaoliang/` (type check, build, post-build checks) and copies its output to `dist/` |
| `.node-version` | Node.js major version Cloudflare uses for the build |

## Cloudflare Pages settings

- Production branch: `master` (other branches get preview deployments)
- Root directory: `_deploy/xiaoliang-group`
- Build command: `bash build.sh`
- Build output directory: `dist`

## Local build

```bash
bash _deploy/xiaoliang-group/build.sh     # output in _deploy/xiaoliang-group/dist/
```
