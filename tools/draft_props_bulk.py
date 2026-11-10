"""Localize result/prop textures using ImageGen lettering and protected originals."""
from pathlib import Path
import json,shutil,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import label,find_objects,binary_dilation,binary_fill_holes
from scipy.spatial import ConvexHull
R=Path(__file__).resolve().parents[1];O=R/'work/graphics-draft/props-bulk-v1';D=O/'imagegen'
def rgba(p):return np.array(Image.open(p).convert('RGBA'))
def palette(a,b):
 colors=np.unique(a.reshape(-1,4),axis=0);opaque=colors[colors[:,3]>0];flat=b.reshape(-1,4).astype('int32');out=flat.copy()
 for st in range(0,len(flat),512):
  q=flat[st:st+512];ix=((q[:,None,:]-opaque[None,:,:].astype('int32'))**2).sum(2).argmin(1);out[st:st+len(q)]=opaque[ix]
 transparent=colors[colors[:,3]==0]
 if len(transparent):out[flat[:,3]<100]=transparent[0]
 return out.astype('uint8').reshape(b.shape)
def text_components(a,minx,threshold=0):
 lab,n=label(a[:,:,3]>threshold);m=np.zeros(a.shape[:2],bool)
 for k,sl in enumerate(find_objects(lab),1):
  if sl[1].start>=minx and (lab[sl]==k).sum()>20:m|=lab==k
 return m
def main():
 w={i['id']:i for i in json.loads((R/'metadata/graphics_worklist.json').read_text('utf8'))['items']};specs=json.loads((D/'prompts.json').read_text('utf8'))['specs'];entries=[];cards=[]
 for s in specs:
  key=s['id'];raw=D/(key+'-generated.png')
  if not raw.exists():shutil.copy2(s['generated_path'],raw)
  if key=='T0420':
   rev=json.loads((D/'T0420-revision.json').read_text('utf8'));raw=D/'T0420-generated-v2.png'
   if not raw.exists():shutil.copy2(rev['generated_path'],raw)
  src=R/'work/graphics-review'/w[key]['assets'][0]['image'];a=rgba(src);im=Image.fromarray(a);gen=Image.open(raw).convert('RGBA');q=np.array(gen.resize(im.size,Image.Resampling.LANCZOS));b=a.copy();old=np.zeros(a.shape[:2],bool);new=old.copy()
  if key in ('T1703','T1704'):
   old=text_components(a,35);ys,xs=np.where(old);box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
   gm=text_components(q,40,100);gy,gx=np.where(gm);crop=gen.crop((gx.min()/128*gen.width,gy.min()/64*gen.height,(gx.max()+1)/128*gen.width,(gy.max()+1)/64*gen.height));glyph=crop.resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
   b[old]=[0,0,0,0];clean=Image.fromarray(b);overlay=np.zeros_like(a);overlay[box[1]:box[3],box[0]:box[2]]=np.array(glyph);new=overlay[:,:,3]>100;dark=overlay[:,:,:3].max(2)<110;overlay[dark&new,:3]=0;overlay[new,3]=255;b[new]=overlay[new]
   # Extend only the outer black stroke, leaving the glyph fill and character intact.
   character=(a[:,:,3]>0)&~old
   outer=binary_dilation(new&~dark,iterations=2)&~new&~character
   b[outer]=[0,0,0,255];new|=outer
   Image.fromarray(outer.astype('uint8')*255).save(D/(key+'-outline-added-v7.png'))
   note='흰 테두리 바깥 검은 외곽선을 원본처럼 약 2px 두께로 보강. 글자 색·흰 테두리·위치와 분리된 원본 캐릭터 픽셀 보존.'
  elif key=='T1702':
   from props_intact_police import compose
   b,old,new=compose(a,q,R/'work/scope-followup/textures/T1703.png',D)
   clean=Image.fromarray(b)
   note='실패! 원본의 온전한 돼지를 왼쪽에 재사용. 불합격!의 초기 글자 폭을 복구하고 실패!와 같은 37px 높이로 배치. 캐릭터 크기·실루엣 유지, 대상 원본 팔레트로 색상 변환.'
  elif key=='T0069':
   rgb=a[:,:,:3].astype(int);region=np.zeros(a.shape[:2],bool);region[8:58,10:38]=True
   old=region&((rgb.max(2)-rgb.min(2)<45)|((rgb[:,:,1]>90)&(rgb[:,:,2]>70)))
   for y in range(8,58):
    candidates=a[y,[7,8,39,40]];color=candidates[2] if candidates[2,0]>candidates[2,1]*1.5 else candidates[0]
    b[y,old[y]]=color
   clean=Image.fromarray(b);full=np.array(gen);rgb=full[:,:,:3].astype(int);roi=np.zeros(full.shape[:2],bool)
   roi[round(7/64*gen.height):round(57/64*gen.height),round(9/64*gen.width):round(33/64*gen.width)]=True
   whites=(rgb.min(2)>145)&roi;hullmask=Image.new('L',gen.size);hd=ImageDraw.Draw(hullmask)
   for y0,y1 in [(7,23),(23,39),(39,57)]:
    section=whites.copy();section[:round(y0/64*gen.height)]=False;section[round(y1/64*gen.height):]=False
    hy,hx=np.where(section);pts=np.column_stack((hx,hy));hull=ConvexHull(pts);hd.polygon([tuple(map(int,p)) for p in pts[hull.vertices]],fill=255)
   enclosed=np.array(hullmask)>0
   glyphmask=enclosed&(rgb.max(2)-rgb.min(2)<90)
   ys,xs=np.where(glyphmask);box=(xs.min(),ys.min(),xs.max()+1,ys.max()+1);g=gen.crop(box);m=Image.fromarray(glyphmask.astype('uint8')*255).crop(box)
   g=g.resize((27,49),Image.Resampling.LANCZOS);m=m.resize((27,49),Image.Resampling.LANCZOS);new[8:57,10:37]=np.array(m)>100;overlay=np.zeros_like(a);overlay[8:57,10:37]=np.array(g);b[new]=overlay[new]
   note='이미지젠 세로 글씨 뇌·신·문. 글자와 분리된 어두운 점 6px를 주변 붉은 바탕색으로 정리. 글자 획·등롱 무늬·우측 부품 보존.'
  else:
   yy,xx=np.indices(a.shape[:2]);ar=a[:,:,:3].astype(int);qr=q[:,:,:3].astype(int)
   old=(ar[:,:,0]>ar[:,:,1]*1.65)&(ar[:,:,0]-ar[:,:,1]>45)&(yy<40)
   old=binary_dilation(old,iterations=1)&(yy<40)
   new=(qr[:,:,0]>qr[:,:,1]*1.65)&(qr[:,:,0]-qr[:,:,1]>45)&(yy<40)
   b[old|new]=q[old|new];clean=Image.fromarray(a)
   note='이미지젠 제니. 기존 일본어와 붉은 잔상 마스크를 복원. 하단 화살표·배경·테두리의 마스크 밖 원본 픽셀 보존.'
  out=palette(a,b)
  if key=='T0069':
   # Only six isolated dark-red specks; never replace connected black glyph strokes.
   for x,y in [(26,11),(14,23),(26,23),(25,26),(26,28),(20,32)]:
    assert tuple(out[y,x])==(49,8,0,255)
    out[y,x]=[206,33,0,255];old[y,x]=True
  if key=='T1702':
   from props_intact_police import preserve_character_alpha
   out=preserve_character_alpha(a,out,R/'work/scope-followup/textures/T1703.png',D/'T1702-visible-character-mask-v6.png')
  allowed=old|new;out[~allowed]=a[~allowed];assert not np.any(np.any(out!=a,2)&~allowed),(key,'outside mask')
  assert set(map(tuple,out.reshape(-1,4)))<=set(map(tuple,a.reshape(-1,4)))
  Image.fromarray(out).save(O/(key+'-ko.png'));Image.fromarray(allowed.astype('uint8')*255).save(D/(key+'-edit-mask.png'))
  notes=[note,'원본 텍스처 크기·팔레트 유지. 게임 내 합성·표시는 추후 확인.']
  e=dict(id=key+'/texture',group=key,cell=None,source=w[key]['assets'][0]['image'],result_image='../graphics-draft/props-bulk-v1/'+key+'-ko.png',reading=s['jp'],translation=s['ko'].replace(' ',''),notes=notes,size=list(im.size),stage='draft',method='imagegen',checks=dict(palette_preserved=True,outside_edit_mask_preserved=True,changed_pixels=int(np.any(out!=a,2).sum())),runtime_verified=False,rom_inserted=False);entries.append(e)
  views=[]
  for scale in (1,4):
   views.append('<div class="pair">'+''.join(f'<figure><figcaption>{lab} · {scale}배</figcaption><span class="bg"><img src="{p}" width="{im.width*scale}" height="{im.height*scale}"></span></figure>' for lab,p in [('원본','../../graphics-review/'+e['source']),('한국어',key+'-ko.png?revision=lantern-specks-v8')])+'</div>')
  cards.append(f'<article id="{key}"><h2>{key} · {e["translation"]}</h2><p>{s["jp"]}</p>'+''.join(views)+'<p>'+html.escape(' '.join(notes))+'</p></article>')
 css='body{font:16px sans-serif;background:#edf1e7;margin:24px;color:#172028}main{max-width:1250px;margin:auto}article{background:white;padding:24px;margin:20px 0;border-radius:12px}.pair{display:flex;flex-wrap:wrap;gap:30px;margin:20px 0}figure{margin:0}figcaption{margin:8px 0}img{image-rendering:pixelated}.bg{display:inline-block;background:repeating-conic-gradient(#ddd 0% 25%,white 0% 50%) 0/8px 8px}'
 (O/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>결과 표시·소품 글씨 5개</title><style>'+css+'</style><main><a href="../../graphics-review/dashboard.html">카테고리 현황판</a><h1>결과 표시·소품 글씨 · 5개</h1><p>불합격·실패·합격 / 뇌신문·제니. 이미지젠 수정안, ROM 반영 전 검토용.</p>'+''.join(cards)+'</main></html>','utf8')
 (R/'metadata/graphics_props_bulk_draft_v1.json').write_text(json.dumps(dict(batch='props-bulk-v1',entries=entries,rom_modified=False),ensure_ascii=False,indent=2)+'\n','utf8')
 sheet=Image.new('RGB',(1100,1450),'#aaa');draw=ImageDraw.Draw(sheet)
 for i,e in enumerate(entries):
  draw.text((0,i*290),e['id'],fill='black')
  for j,key in enumerate(['source','result_image']):
   p=Image.open(R/'work/graphics-review'/e[key]).convert('RGBA');p=p.resize((p.width*4,p.height*4),Image.Resampling.NEAREST);sheet.paste(p,(j*550,i*290+20),p)
 sheet.save(O/'composite-qa.png');print('5 drafts; exact palette and pixels outside masks verified.')
if __name__=='__main__':main()
