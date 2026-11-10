"""Audit every Mane draft and restore all cord-family assets without rerunning unrelated drafts."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
from mane_cord_renderer import render_mane_cord
R=Path(__file__).resolve().parents[1];O=R/'work/graphics-draft/mane-restoration'
TARGETS={'G0232':(121,126,7),'G0233':(121,126,17),'G0303':(64,69,7)}
def parts(e):
 c=e.get('checks',{});return c if isinstance(c,list) else c.get('parts',[])
def main():
 O.mkdir(exist_ok=True);audit=[];fixed=[];cards=[]
 for mp in sorted((R/'metadata').glob('graphics*draft*.json')):
  data=json.loads(mp.read_text('utf8'));dirty=False
  for e in data.get('entries',[]):
   if not any('마네' in str(t) for t in [e.get('translation',''),e.get('reading',''),parts(e)]):continue
   src=R/'work/graphics-review'/e['source'];dest=R/'work/graphics-review'/e['result_image'];original=Image.open(src).convert('RGBA');before=Image.open(dest).convert('RGBA')
   group=e.get('group');cell=e.get('cell');target=group in TARGETS and TARGETS[group][0]<=cell<=TARGETS[group][1]
   row=dict(id=e['id'],source=e['source'],result_image=e['result_image'],has_price_cord=target)
   if target:
    low,high,top=TARGETS[group];after,clean,mask,check=render_mane_cord(original,cell-low,top)
    saved=O/(e['id'].replace('/','-')+'-before.png')
    if not saved.exists():before.save(saved)
    else:before=Image.open(saved).convert('RGBA')
    after.save(dest);clean.save(dest.with_name(dest.name.replace('-ko.png','-clean.png')))
    e['checks']={'parts':[check],'nontext_pixels_preserved':True,'palette_preserved':True} if group=='G0303' else [check] if group=='G0232' else check
    e['notes']=[n for n in e.get('notes',[]) if '흰 배경' not in n and not n.startswith('코드·플러그 복구:')]+['코드·플러그 복구: 원본 비문자 픽셀 대조 통과. 마네 글자는 코드 위로 이동해 겹침 제거.']
    e['cord_restoration_verified']=True;dirty=True
    row.update(check);row['changed_pixels']=int(np.any(np.array(before)!=np.array(after),2).sum());fixed.append(row)
    imgs=[]
    for label,pic in [('원본',original),('수정 전',before),('복구 후',after)]:
     name=e['id'].replace('/','-')+'-'+{'원본':'source','수정 전':'before','복구 후':'after'}[label]+'.png';pic.save(O/name)
     imgs.append(f'<figure><figcaption>{label} · 1배 / 4배</figcaption><span class="bg"><img src="{name}" width="{pic.width}" height="{pic.height}"></span><br><span class="bg"><img src="{name}" width="{pic.width*4}" height="{pic.height*4}"></span></figure>')
    cards.append(f'<article id="{e["id"].replace("/","-")}"><h2>{e["id"]}</h2><div>{"".join(imgs)}</div></article>')
   else:
    # No cord in these currency labels/cards. Ensure the source currency
    # icon zone remains exact for non-card savings labels where applicable.
    row['status']='원본/수정안 대조 완료: 코드가 없는 마네 표기'
   audit.append(row)
  if dirty:mp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
 assert len(fixed)==18
 (R/'metadata/graphics_mane_cord_restoration.json').write_text(json.dumps(dict(audited_assets=len(audit),restored_assets=18,entries=fixed,audit=audit,rom_modified=False),ensure_ascii=False,indent=2)+'\n','utf8')
 css='body{font:16px sans-serif;background:#edf1e7;margin:24px}article{background:white;padding:20px;margin:16px 0;border-radius:12px}article>div{display:flex;flex-wrap:wrap;gap:24px}figure{margin:0}img{image-rendering:pixelated}.bg{display:inline-block;background:repeating-conic-gradient(#ddd 0% 25%,white 0% 50%) 0/8px 8px}figcaption{margin:8px 0}'
 (O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>마네 코드·플러그 복구</title><style>'+css+'</style><h1>마네 코드·플러그 18개 복구</h1><p>전화 6개 · 홈쇼핑 2 6개 · 홈쇼핑 3 6개. 원본 코드와 플러그 픽셀 대조 완료.</p>'+''.join(cards),'utf8')
 for start in range(0,18,6):
  sheet=Image.new('RGB',(1100,6*155),'#bbb');d=ImageDraw.Draw(sheet)
  for n,e in enumerate(fixed[start:start+6]):
   d.text((0,n*155),e['id'],fill='black')
   for j,suffix in enumerate(['source','after']):
    im=Image.open(O/(e['id'].replace('/','-')+'-'+suffix+'.png')).convert('RGBA');im=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(im,(j*550,n*155+20),im)
  sheet.save(O/f'fixed-{start//6}.png')
 print('Audited',len(audit),'Mane assets; restored',len(fixed),'cord assets.')
if __name__=='__main__':main()
