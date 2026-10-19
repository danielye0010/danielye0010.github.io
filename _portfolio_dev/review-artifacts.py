from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
import json, re
root=Path(__file__).resolve().parents[1]
a=root/'_site/xiaoliang';b=root/'_portfolio_dev/baseline-site/xiaoliang'
files=[p for p in a.rglob('*') if p.is_file()]
def normalized(p):
 if p.suffix!='.html':return p.read_bytes()
 s=p.read_text(encoding='utf-8')
 s=re.sub(r'"dateModified": "[^"]+"','"dateModified": "BUILD_TIME"',s)
 return re.sub(r'xl.css\?v=\d+','xl.css?v=BUILD_TIME',s)
diffs=[str(p.relative_to(a)) for p in files if not (b/p.relative_to(a)).exists() or normalized(p)!=normalized(b/p.relative_to(a))]
(root/'_portfolio_dev/regression-check.json').write_text(json.dumps({'compared':len(files),'normalization':'Only dateModified and xl.css build timestamp','differences':diffs},indent=2))
photos=list((root/'assets/img/manufacturing').glob('*.webp'))
sheet=Image.new('RGB',(1200,350*((len(photos)+2)//3)),'#f4f0f6');draw=ImageDraw.Draw(sheet)
for i,p in enumerate(photos):
 im=Image.open(p);im.thumbnail((370,270));x=20+(i%3)*400;y=20+(i//3)*350
 sheet.paste(im,(x+(370-im.width)//2,y+(270-im.height)//2));draw.text((x,y+285),p.name,fill='#29222f')
sheet.save(root/'_portfolio_dev/gallery-proof.jpg',quality=90)
print(json.dumps({'regression_differences':diffs,'gallery_photos':len(photos)}))
