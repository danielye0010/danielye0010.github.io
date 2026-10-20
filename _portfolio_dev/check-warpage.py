"""Validate the rendered paper page and research entry links."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
root = Path(__file__).resolve().parents[1] / '_site'
page = root / 'papers/structure-aligned-compensation/index.html'
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]; self.ids=set()
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        for k in ('href','src'):
            if k in a: self.urls.append(a[k])
p=Links(); html=page.read_text(encoding='utf-8'); p.feed(html)
errors=[]
for url in p.urls:
    u=urlsplit(url)
    if u.scheme or u.netloc: continue
    target=root/unquote(u.path).lstrip('/') if u.path.startswith('/') else page.parent/unquote(u.path)
    if not u.path: target=page
    if target.is_dir(): target=target/'index.html'
    if not target.exists(): errors.append('Missing '+url)
    if u.fragment and target==page and u.fragment not in p.ids: errors.append('Missing anchor '+url)
for value in ('0.014','0.0061','2.94','2.07'):
    if value not in html: errors.append('Missing paper table value '+value)
for lang in ('','zh/'):
    research=(root/lang/'research/index.html').read_text(encoding='utf-8')
    if 'href="/papers/structure-aligned-compensation/">Website' not in research: errors.append('Missing Website link '+lang)
if (root/'responsive-qa.html').exists(): errors.append('QA harness leaked into final build')
report={'links_checked':len(p.urls),'table_values_checked':4,'errors':errors}
print(json.dumps(report,indent=2))
raise SystemExit(bool(errors))
