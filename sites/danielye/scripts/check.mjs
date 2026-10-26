// Post-build checks for https://danielye.net/. Exits non-zero on any problem, which stops the deploy.
//   node scripts/check.mjs dist
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const out = process.argv[2] ?? 'dist';
const origin = 'https://danielye.net';
const errors = [];

// Files that search engines, the custom domain, or other sites depend on.
const required = [
  'CNAME', 'robots.txt', 'sitemap.xml', 'llms.txt',
  'google832a9f381c11f45f.html', // Google Search Console verification
  'd48e99ff3f3e2223b56b1152af5fe7c8.txt', // IndexNow key
  'assets/img/danielavatar.jpg', 'assets/img/favicon_black.png',
  'papers/structure-aligned-compensation/index.html',
  'manufacturing/index.html', 'zh/manufacturing/index.html',
  'xiaoliang/index.html', 'xiaoliang/zh/index.html',
];
for (const f of required) if (!existsSync(join(out, f))) errors.push(`missing ${f}`);
if (existsSync(join(out, 'CNAME')) && readFileSync(join(out, 'CNAME'), 'utf8').trim() !== 'danielye.net') errors.push('CNAME is not danielye.net');

// Every page in the sitemap must exist, and declare itself as canonical.
const sitemap = readFileSync(join(out, 'sitemap.xml'), 'utf8');
const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
if (locs.length < 10) errors.push(`sitemap lists only ${locs.length} pages`);
for (const loc of locs) {
  if (!loc.startsWith(`${origin}/`)) { errors.push(`sitemap: foreign URL ${loc}`); continue; }
  const file = join(out, loc.slice(origin.length), 'index.html');
  if (!existsSync(file)) { errors.push(`sitemap: ${loc} has no page`); continue; }
  const canonical = readFileSync(file, 'utf8').match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  if (canonical !== loc) errors.push(`${relative(out, file)}: canonical is ${canonical}, expected ${loc}`);
}

const walk = (dir) => readdirSync(dir).flatMap((n) => (statSync(join(dir, n)).isDirectory() ? walk(join(dir, n)) : [join(dir, n)]));
const htmlFiles = walk(out).filter((f) => f.endsWith('.html'));
for (const f of htmlFiles) {
  const body = readFileSync(f, 'utf8');
  const rel = relative(out, f);
  // Every root-relative href/src must resolve to a built file.
  for (const [, link] of body.matchAll(/(?:href|src)="(\/[^"]*)"/g)) {
    if (link.startsWith('//')) continue;
    const path = decodeURI(link.split(/[?#]/)[0]);
    const target = path.endsWith('/') ? join(out, path, 'index.html') : join(out, path);
    if (!existsSync(target)) errors.push(`${rel}: broken link ${link}`);
  }
  // Structured data must be valid JSON.
  for (const [, json] of body.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
    try { JSON.parse(json); } catch (e) { errors.push(`${rel}: invalid JSON-LD (${e.message})`); }
  }
}

if (errors.length) {
  for (const e of errors) console.error(`check: ${e}`);
  process.exit(1);
}
console.log(`check: OK (${htmlFiles.length} HTML files, ${locs.length} sitemap URLs)`);
