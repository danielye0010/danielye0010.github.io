"""Check rendered personal routes, assets, translations, and private-file exclusion."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
base=sys.argv[2] if len(sys.argv)>2 else ''
class Page(HTMLParser):
 def __init__(self): super().__init__();self.urls=[];self.ids=set()
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.add(a['id'])
  for key in ('href','src'):
   if key in a:self.urls.append((tag,a[key]))
errors=[];count=0
for lang in ('','zh/'):
 for kind in ('','research/','engineering/','projects/'):
  file=root/lang/kind/'index.html'; p=Page();p.feed(file.read_text(encoding='utf-8'))
  for tag,url in p.urls:
   u=urlsplit(url)
   if u.scheme or u.netloc or not u.path:continue
   pathname=unquote(u.path)
   if base and pathname.startswith(base+'/'):pathname=pathname[len(base):]
   target=root/pathname.lstrip('/') if pathname.startswith('/') else file.parent/pathname
   if target.is_dir():target=target/'index.html'
   count+=1
   if not target.exists():errors.append(f'{file}: missing {url}')
   elif u.fragment and target.suffix=='.html':
    q=Page();q.feed(target.read_text(encoding='utf-8'))
    if u.fragment not in q.ids:errors.append(f'{file}: missing anchor {url}')
for forbidden in ('_portfolio_dev','PORTFOLIO_HANDOFF.md','ASSET_MANIFEST.json'):
 if list(root.rglob(forbidden)):errors.append(f'Development artifact published: {forbidden}')
report={'root':str(root),'baseurl':base,'checked_local_links':count,'errors':errors}
print(json.dumps(report,indent=2));sys.exit(bool(errors))
