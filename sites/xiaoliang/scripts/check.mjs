// Post-build checks for https://xiaoliang.group/. Exits non-zero on any problem, which fails the deploy.
//   node scripts/check.mjs dist
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const out = process.argv[2] ?? 'dist';
const errors = [];

const required = ['index.html', 'zh/index.html', '404.html', 'llms.txt', 'robots.txt', 'sitemap.xml', '_redirects', 'assets/avatar.jpg', 'assets/logo-512.png'];
for (const f of required) if (!existsSync(join(out, f))) errors.push(`missing ${f}`);

const walk = (dir) => readdirSync(dir).flatMap((n) => (statSync(join(dir, n)).isDirectory() ? walk(join(dir, n)) : [join(dir, n)]));
const textFiles = walk(out).filter((f) => /\.(html|txt|xml)$/.test(f));

for (const f of textFiles) {
  const body = readFileSync(f, 'utf8');
  const rel = relative(out, f);
  // Leftovers from the old danielye.net/xiaoliang/ deployment.
  if (body.includes('/xiaoliang/')) errors.push(`${rel}: contains '/xiaoliang/'`);
  if (body.includes('danielye.net')) errors.push(`${rel}: contains 'danielye.net'`);
  if (!f.endsWith('.html')) continue;

  // Every root-relative href/src must resolve to a built file.
  for (const [, link] of body.matchAll(/(?:href|src)="(\/[^"]*)"/g)) {
    if (link.startsWith('//')) continue;
    const path = link.split(/[?#]/)[0];
    const target = path.endsWith('/') ? join(out, path, 'index.html') : join(out, path);
    if (!existsSync(target)) errors.push(`${rel}: broken link ${link}`);
  }
  // Structured data must be valid JSON.
  for (const [, json] of body.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
    try { JSON.parse(json); } catch (e) { errors.push(`${rel}: invalid JSON-LD (${e.message})`); }
  }
}

// Canonical URLs must point at the right page on the domain.
for (const [f, want] of [['index.html', 'https://xiaoliang.group/'], ['zh/index.html', 'https://xiaoliang.group/zh/']]) {
  const got = readFileSync(join(out, f), 'utf8').match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  if (got !== want) errors.push(`${f}: canonical is ${got}, expected ${want}`);
}

if (errors.length) {
  for (const e of errors) console.error(`check: ${e}`);
  process.exit(1);
}
console.log(`check: OK (${textFiles.length} text files checked)`);
