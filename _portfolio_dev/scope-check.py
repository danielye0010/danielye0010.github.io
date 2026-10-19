from pathlib import Path
import hashlib, json, subprocess
root=Path(__file__).resolve().parents[1]
changed=subprocess.check_output(['git','diff','--name-only','master'],cwd=root,text=True).splitlines()
protected=('xiaoliang/','_deploy/','_layouts/xl.html','_includes/xl/','_data/xl.yml','_sass/','.github/','CNAME','sitemap.xml','robots.txt')
violations=[p for p in changed if p.startswith(protected)]
manifest=json.loads((root/'_portfolio_dev/ASSET_MANIFEST.json').read_text())
hashes=[]
for p in (root/'assets/img/manufacturing').glob('*.webp'):
 original=next(x for x in manifest if x['filename']==p.name)
 hashes.append({'file':p.name,'matches_source':hashlib.sha256(p.read_bytes()).hexdigest()==original['sha256']})
report={'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip(),'baseline':subprocess.check_output(['git','rev-parse','master'],cwd=root,text=True).strip(),'protected_path_changes':violations,'photos':hashes}
(root/'_portfolio_dev/scope-check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
assert not violations and all(x['matches_source'] for x in hashes)
