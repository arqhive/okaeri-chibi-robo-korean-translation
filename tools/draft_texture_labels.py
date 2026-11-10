"""Native Galmuri drafts for six length markers and four dust/mold textures."""
from pathlib import Path
import json,html,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from draft_ui01_graphics import glyph
R=Path(__file__).resolve().parents[1]
O=R/'work/graphics-draft/texture-labels-v1'

def white_glyph(text,scale,font_name='Galmuri7',font_px=8):
 font=ImageFont.truetype(str(Path.home()/f'AppData/Local/Microsoft/Windows/Fonts/{font_name}.ttf'),font_px)
 mask=Image.new('L',(256,40));d=ImageDraw.Draw(mask);d.fontmode='1';d.text((1,1),text,font=font,fill=255)
 mask=mask.crop(mask.getbbox());mask=mask.resize((mask.width*scale,mask.height*scale),Image.Resampling.NEAREST)
 g=Image.new('RGBA',mask.size,(255,255,255,0));g.putalpha(mask);return g

def mold_malgun(text):
 font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',18)
 mask=Image.new('L',(128,40));d=ImageDraw.Draw(mask);d.fontmode='1';x=0
 for ch in text:
  d.text((x,0),ch,font=font,fill=255);x+=round(font.getlength(ch))-1
 mask=mask.crop(mask.getbbox());assert mask.size==(61,17)
 # At 18px the monochrome hinting drops both joins under the upper bar
 # of the initial pieup in 팡. Repair only that initial consonant.
 assert text=='곰팡이~'
 pixels=np.array(mask);pixels[1:9,17:28]=0
 pixels[1,17:28]=255;pixels[8,17:28]=255
 pixels[2:8,19]=255;pixels[2:8,24]=255
 mask=Image.fromarray(pixels)
 g=Image.new('RGBA',mask.size,(255,255,255,0));g.putalpha(mask);return g

def main():
 O.mkdir(exist_ok=True);w=json.loads((R/'metadata/graphics_worklist.json').read_text('utf8'));entries=[];cards=[]
 for it in w['items']:
  if it['work_group'] not in ('length','dust'):continue
  asset=it['assets'][0];src=R/'work/graphics-review'/asset['image'];im=Image.open(src).convert('RGBA');a=np.array(im);b=a.copy();allowed=np.zeros(a.shape[:2],bool);parts=[]
  if it['work_group']=='length':
   old=(a[:,:,3]>0);old[:,32:]=False
   b[old]=[0,247,255,0];g=glyph('처음','white_black',0);placements=[(0,4)];text='처음 '+it['reading'].split()[-1]
   note='갈무리7. 처음 표기만 교체하고 숫자와 cm는 원본 픽셀 그대로 보존.'
  else:
   text='곰팡이~' if 'Fungus' in it['name'] else '먼지'
   old=np.all(a==[255,255,255,255],axis=2);b[old]=a[0,0]
   ys=np.flatnonzero(old.any(axis=1));runs=np.split(ys,np.where(np.diff(ys)>1)[0]+1);assert len(runs)==3
   scale=4 if im.width==128 else 2
   if it['id']=='D0017':scale=1;g=mold_malgun(text)
   else:g=white_glyph(text,scale)
   assert g.width<=im.width
   placements=[((im.width-g.width)//2,int(v[0])+(len(v)-g.height)//2) for v in runs]
   note=f'갈무리7 {scale}배 정수 확대. 원본 3줄 반복과 각 줄의 세로 중심 유지. 흰 글자 획만 제거하고 단색 배경 보존.'
   if it['id']=='D0017':note='맑은 고딕 18px · 글자 높이 17px. 팡의 ㅍ 획 연결·두께 보정. 녹색 배경과 원본 3줄 위치 유지.'
  allowed|=old;clean=Image.fromarray(b);out=clean.copy()
  for x,y in placements:
   assert x>=0 and y>=0 and x+g.width<=im.width and y+g.height<=im.height
   out.alpha_composite(g,(x,y));allowed[y:y+g.height,x:x+g.width]|=np.array(g)[:,:,3]>0;parts.append(dict(text=text,position=[x,y],glyph_size=list(g.size)))
  generated=O/'imagegen'/(it['id']+'-native.png')
  imagegen=it['id'] in ('D0015','D0016') and generated.exists()
  if imagegen:
   out=Image.open(generated).convert('RGBA');assert out.size==im.size
   allowed=old|np.all(np.array(out)==[255,255,255,255],axis=2)
   note='이미지젠. 원본의 손글씨 느낌과 3줄 반복 유지. 원본 크기·배경색·2색 팔레트로 적용.'
   parts=[dict(text=text,method='imagegen',source='imagegen/'+it['id']+'-generated.png')]
  oa=np.array(out);assert not np.any(np.any(oa!=a,axis=2)&~allowed)
  assert set(map(tuple,oa.reshape(-1,4)))<=set(map(tuple,a.reshape(-1,4)))
  if it['work_group']=='length':assert np.array_equal(oa[:,32:],a[:,32:])
  stem=it['id']+'-texture';out.save(O/(stem+'-ko.png'));clean.save(O/(stem+'-clean.png'))
  e=dict(id=it['id']+'/texture',group=it['id'],cell=None,source=asset['image'],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),result_image='../graphics-draft/texture-labels-v1/'+stem+'-ko.png',reading=it['reading'],translation=text,notes=[note,'3D 모델에 적용되기 전 텍스처 원판. 게임 내 표시는 추후 확인.'],size=list(im.size),stage='draft',font='Galmuri7',checks=dict(parts=parts,nontext_pixels_preserved=True,palette_preserved=True,numbers_preserved=it['work_group']=='length'),runtime_verified=False,rom_inserted=False)
  if imagegen:e.update(font=None,method='imagegen')
  if it['id']=='D0017':e.update(font='Malgun Gothic',font_px=18,tracking_px=-1,ink_height=17,method='font')
  entries.append(e);views=[]
  for s in [1,4 if im.width<=64 else 2]:
   pair=''.join(f'<figure><figcaption>{label} · {s}배</figcaption><span class="bg"><img src="{html.escape(path)}" width="{im.width*s}" height="{im.height*s}" alt="{html.escape(text)}"></span></figure>' for label,path in [('원본','../../graphics-review/'+e['source']),('한국어',stem+'-ko.png')])
   views.append('<div class="pair">'+pair+'</div>')
  cards.append(f'<article id="{it["id"]}"><h2>{it["id"]} · {html.escape(text)}</h2><p>{html.escape(it["reading"])}</p>'+''.join(views)+f'<p>{note}</p></article>')
 assert len(entries)==10
 (R/'metadata/graphics_texture_labels_draft_v1.json').write_text(json.dumps(dict(batch='texture-labels-v1',entries=entries,edited_textures=10,rom_modified=False),ensure_ascii=False,indent=2)+'\n','utf8')
 css='body{font:16px sans-serif;background:#edf1e7;color:#172028;margin:24px}main{max-width:1200px;margin:auto}article{padding:24px;background:white;border-radius:12px;margin:20px 0}.pair{display:flex;flex-wrap:wrap;gap:40px;margin:20px 0}figure{margin:0}figcaption{margin:8px 0;color:#52636a}img{image-rendering:pixelated}.bg{display:inline-block;background:repeating-conic-gradient(#ddd 0% 25%,white 0% 50%) 0/8px 8px}'
 page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>길이 기록·먼지·곰팡이 10개</title><style>'+css+'</style><main><a href="../../graphics-review/dashboard.html">카테고리 현황판</a><h1>길이 기록·먼지·곰팡이 · 10개</h1><p>길이 기록 6개 · 먼지와 곰팡이 4개. D0015·D0016·D0017은 이미지젠 수정안입니다.</p><p>3D 소품에 입히는 텍스처 원판입니다. ROM 반영 전 검토용입니다.</p>'+''.join(cards)+'</main></html>'
 page=page.replace('D0015·D0016·D0017은 이미지젠 수정안입니다.','D0015·D0016은 이미지젠, D0017은 맑은 고딕 수정안입니다.')
 page=page.replace('-texture-ko.png"','-texture-ko.png?revision=d0017-pieup-v5"')
 (O/'index.html').write_text(page,'utf8');print('10 texture drafts; nontext, palette and number preservation passed.')
if __name__=='__main__':main()
