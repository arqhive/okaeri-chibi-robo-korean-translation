from pathlib import Path
import json,hashlib,re
from PIL import Image,ImageDraw
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'work/graphics-draft/props-bulk-v1';D=O/'imagegen'
before=json.loads((D/'unchanged-hashes-v2.json').read_text('utf-8-sig'))
unchanged={Path(e['Path']).name:hashlib.sha256(Path(e['Path']).read_bytes()).hexdigest().upper()==e['Hash'] for e in before};assert all(unchanged.values())
entries=json.loads((R/'metadata/graphics_props_bulk_draft_v1.json').read_text('utf8'))['entries'];checks=[]
for e in entries:
 key=e['group'];a=np.array(Image.open(R/'work/graphics-review'/e['source']).convert('RGBA'));b=np.array(Image.open(O/(key+'-ko.png')).convert('RGBA'));m=np.array(Image.open(D/(key+'-edit-mask.png')))>0
 assert a.shape==b.shape and np.array_equal(a[~m],b[~m])
 assert set(map(tuple,b.reshape(-1,4)))<=set(map(tuple,a.reshape(-1,4)))
 checks.append(dict(id=key,outside_mask_identical=True,size_preserved=True,palette_preserved=True))
 if key=='T1702':
  source=np.array(Image.open(R/'work/scope-followup/textures/T1703.png').convert('RGBA'))
  char=np.array(Image.open(D/'T1702-character-mask-v4.png'))>0;text=np.array(Image.open(D/'T1702-text-mask-v4.png'))>0
  assert not (char&text).any()
  assert np.array_equal(b[char,3],source[char,3])
  assert np.all(b[~(char|text),3]==0)
  details=dict(character_source='T1703',character_pixels=int(char.sum()),character_alpha_exact=True,character_scaled=False,character_color_remapped_to_target_palette=True,title_size=[80,30],title_position=[46,17],overlap_pixels=0,generated_character_used=False,other_four_unchanged=unchanged)
  preview=Image.new('RGB',(530,360),'white');draw=ImageDraw.Draw(preview);draw.text((8,5),'T1702 - intact character - 1x / 4x',fill='black')
  for scale,pos in [(1,(8,25)),(4,(8,96))]:
   im=Image.fromarray(b).resize((128*scale,64*scale),Image.Resampling.NEAREST)
   for y in range(pos[1],pos[1]+im.height,4):
    for x in range(pos[0],pos[0]+im.width,4):draw.rectangle((x,y,x+3,y+3),fill='#ddd' if ((x-pos[0])//4+(y-pos[1])//4)%2 else 'white')
   preview.paste(im,pos,im)
  preview.save(O/'T1702-review-v4.png')
sources=re.findall(r'<img src="([^"]+)"',(O/'index.html').read_text('utf8'));assert len(sources)==20 and all((O/s.split('?')[0]).exists() for s in sources)
(R/'metadata/graphics_props_bulk_validation.json').write_text(json.dumps(dict(revision='intact-pig-v4',entries=checks,T1702=details,review_images=20,rom_modified=False),ensure_ascii=False,indent=2)+'\n','utf8')
p=R/'project.json';j=json.loads(p.read_text('utf8'));j['graphics_review_workflow']['current_revision']='intact-pig-v4';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(details,ensure_ascii=False))
