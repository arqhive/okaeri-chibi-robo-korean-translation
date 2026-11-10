from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'work/graphics-draft/props-bulk-v1';D=O/'imagegen'
snapshot=json.loads((D/'unchanged-hashes-v7.json').read_text('utf8'));unchanged={k:hashlib.sha256((O/(k+'-ko.png')).read_bytes()).hexdigest()==v for k,v in snapshot.items()};assert all(unchanged.values())
sheet=Image.new('RGB',(1050,710),'white');draw=ImageDraw.Draw(sheet);checks=[]
for i,k in enumerate(['T1703','T1704']):
 a=np.array(Image.open(R/'work/scope-followup/textures'/(k+'.png')).convert('RGBA'));b=np.array(Image.open(O/(k+'-ko.png')).convert('RGBA'));before=np.array(Image.open(D/(k+'-before-v7.png')).convert('RGBA'));mask=np.array(Image.open(D/(k+'-outline-added-v7.png')))>0
 assert np.array_equal(b[~mask],before[~mask])
 assert np.all(b[mask]==[0,0,0,255])
 assert set(map(tuple,b.reshape(-1,4)))<=set(map(tuple,a.reshape(-1,4)))
 checks.append(dict(id=k,added_black_pixels=int(mask.sum()),outside_outline_exact=True,palette_preserved=True,existing_lettering_and_character_unchanged=True))
 y=i*355;draw.text((8,y+5),k+' original / Korean - 1x and 4x',fill='black')
 for col,arr in enumerate([a,b]):
  for scale,offset in [(1,25),(4,95)]:
   im=Image.fromarray(arr).resize((128*scale,64*scale),Image.Resampling.NEAREST);x=8+col*525;top=y+offset
   for cy in range(top,top+im.height,4):
    for cx in range(x,x+im.width,4):draw.rectangle((cx,cy,cx+3,cy+3),fill='#ddd' if ((cx-x)//4+(cy-top)//4)%2 else 'white')
   sheet.paste(im,(x,top),im)
sheet.save(O/'result-outlines-review-v7.png')
p=R/'metadata/graphics_props_bulk_validation.json';j=json.loads(p.read_text('utf8'));j.update(revision='result-outlines-v7',outline_updates=checks,unchanged_other_assets=unchanged);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
p=R/'project.json';j=json.loads(p.read_text('utf8'));j['graphics_review_workflow']['current_revision']='result-outlines-v7';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(checks,ensure_ascii=False))
