from pathlib import Path
import json,hashlib,re
from PIL import Image,ImageDraw
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'work/graphics-draft/props-bulk-v1';D=O/'imagegen'
before=json.loads((D/'unchanged-hashes-v2.json').read_text('utf-8-sig'))
unchanged={Path(e['Path']).name:hashlib.sha256(Path(e['Path']).read_bytes()).hexdigest().upper()==e['Hash'] for e in before}
assert all(unchanged.values())
entries=json.loads((R/'metadata/graphics_props_bulk_draft_v1.json').read_text('utf8'))['entries'];checks=[]
for e in entries:
 key=e['group'];a=np.array(Image.open(R/'work/graphics-review'/e['source']).convert('RGBA'));b=np.array(Image.open(O/(key+'-ko.png')).convert('RGBA'));m=np.array(Image.open(D/(key+'-edit-mask.png')))>0
 assert a.shape==b.shape and np.array_equal(a[~m],b[~m])
 assert set(map(tuple,b.reshape(-1,4)))<=set(map(tuple,a.reshape(-1,4)))
 checks.append(dict(id=key,outside_mask_identical=True,size_preserved=True,palette_preserved=True))
 if key=='T1702':
  old=np.array(Image.open(D/'T1702-old-letter-mask-v3.png'))>0;new=np.array(Image.open(D/'T1702-new-letter-mask-v3.png'))>0
  # Outside enlarged lettering, every remaining opaque pixel is original.
  visible=(b[:,:,3]>0)&~new
  assert np.array_equal(a[visible],b[visible])
  assert np.array_equal(a[56:],b[56:])
  assert np.all(b[old&~new,3]==0)
  details=dict(title_size=[126,44],title_position=[1,12],generated_character_used=False,visible_character_original=True,other_four_unchanged=unchanged)
  preview=Image.new('RGB',(530,360),'white');draw=ImageDraw.Draw(preview)
  draw.text((8,5),'T1702 - larger title - 1x / 4x',fill='black')
  for scale,pos in [(1,(8,25)),(4,(8,96))]:
   im=Image.fromarray(b).resize((128*scale,64*scale),Image.Resampling.NEAREST)
   for y in range(pos[1],pos[1]+im.height,4):
    for x in range(pos[0],pos[0]+im.width,4):
     draw.rectangle((x,y,x+3,y+3),fill='#ddd' if ((x-pos[0])//4+(y-pos[1])//4)%2 else 'white')
   preview.paste(im,pos,im)
  preview.save(O/'T1702-review-v3.png')
html=(O/'index.html').read_text('utf8');sources=re.findall(r'<img src="([^"]+)"',html)
assert len(sources)==20 and all((O/s.split('?')[0]).exists() for s in sources)
(R/'metadata/graphics_props_bulk_validation.json').write_text(json.dumps(dict(revision='larger-title-v3',entries=checks,T1702=details,review_images=20,rom_modified=False),ensure_ascii=False,indent=2)+'\n','utf8')
p=R/'project.json';j=json.loads(p.read_text('utf8'));j['graphics_review_workflow']['current_revision']='larger-title-v3';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(details,ensure_ascii=False));print('20 review images resolved; all five palette/mask checks passed.')
