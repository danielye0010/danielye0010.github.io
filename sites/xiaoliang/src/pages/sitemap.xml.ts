import type { APIRoute } from 'astro';
import { homeUrl, homeUrlZh } from '../lib/profile';

export const GET: APIRoute = () => {
  const today = new Date().toISOString().slice(0, 10);
  const entry = (loc: string) => `  <url>
    <loc>${loc}</loc>
    <lastmod>${today}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="${homeUrl}"/>
    <xhtml:link rel="alternate" hreflang="zh-Hans" href="${homeUrlZh}"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="${homeUrl}"/>
  </url>`;
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
${entry(homeUrl)}
${entry(homeUrlZh)}
</urlset>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
