"""Localize all shopping cards with explicit masks for three native templates."""
from pathlib import Path
from collections import deque
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from draft_ui01_graphics import glyph
from shopping_card_text import CARDS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/cards-bulk-v1'
BUBBLE={249,256,259,260,282,295,302};BANNER={248,262,263,264,265,266,267}
BLACK=(0,0,0,255);WHITE=(255,255,255,255);YELLOW=(255,255,0,255)
TITLE_FONT=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)

def title_glyph(text,tracking=0):
 mask=Image.new('L',(512,32));draw=ImageDraw.Draw(mask);draw.fontmode='1';x=2
 for ch in text:
  draw.text((x,2),ch,font=TITLE_FONT,fill=255);x+=int(TITLE_FONT.getlength(ch))+tracking
 mask=mask.crop(mask.getbbox());pad=Image.new('L',(mask.width+2,mask.height+2));pad.paste(mask,(1,1))
 outline=pad.filter(ImageFilter.MaxFilter(3));out=Image.new('RGBA',pad.size);out.paste(BLACK,(0,0),outline);out.paste(WHITE,(0,0),pad)
 assert out.height==11
 return out


def lines_image(text,width,style='white_black',maxlines=5):
 lines=text.split('\n')
 assert all(glyph(line,style,0).width<=width for line in lines),(text,width)
 assert len(lines)<=maxlines,(text,lines,maxlines)
 gs=[glyph(s,style,0) for s in lines];out=Image.new('RGBA',(max(g.width for g in gs),10*(len(gs)-1)+9))
 for n,g in enumerate(gs):out.alpha_composite(g,(0,n*10))
 return out,lines

def enclosed_text(a,roi):
 black=np.all(a==BLACK,2)&roi;white=np.all(a==WHITE,2)&roi
 ys,xs=np.where(roi);x0,x1=xs.min(),xs.max();y0,y1=ys.min(),ys.max()
 outside=np.zeros_like(roi);q=deque()
 for y in range(y0,y1+1):
  for x in range(x0,x1+1):
   if (y in (y0,y1) or x in (x0,x1)) and not black[y,x]:outside[y,x]=True;q.append((y,x))
 while q:
  y,x=q.popleft()
  for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
   if y0<=yy<=y1 and x0<=xx<=x1 and not black[yy,xx] and not outside[yy,xx]:outside[yy,xx]=True;q.append((yy,xx))
 return black|(white&~outside)

def main():
 OUT.mkdir(parents=True,exist_ok=True);w=json.loads((ROOT/'metadata/graphics_worklist.json').read_text('utf8'))
 items=[i for i in w['items'] if i['work_group']=='shopping'];assert len(items)==68
 sources={i['id']:np.array(Image.open(ROOT/'work/graphics-review'/i['assets'][0]['image']).convert('RGBA')) for i in items}
 normal=np.array([a for k,a in sources.items() if int(k[1:]) not in BUBBLE|BANNER])
 blue=(normal[:,:,:,2]>=230)&(normal[:,:,:,0]<90)&(normal[:,:,:,1]>=90)&(normal[:,:,:,3]>0)
 entries=[]
 for item in items:
  group=item['id'];n=int(group[1:]);spec=CARDS[group];a=sources[group];b=a.copy();im=Image.fromarray(a);allowed=np.zeros(a.shape[:2],bool);parts=[];draws=[]
  asset=item['assets'][0];src=ROOT/'work/graphics-review'/asset['image']
  source_palette=np.unique(a.reshape(-1,4),axis=0)
  def nearest(color):
   choices=source_palette[source_palette[:,3]==color[3]]
   if not len(choices):return color
   return choices[np.argmin(((choices[:,:3].astype(int)-np.array(color[:3]))**2).sum(1))]
  mode='bubble' if n in BUBBLE else 'banner' if n in BANNER else 'normal'
  def edit(box,text,pos,background,style='white_black',fill=None,width=None,maxlines=1,center=False,masktype='bw'):
   nonlocal b,allowed
   x0,y0,x1,y1=box;roi=np.zeros(a.shape[:2],bool);roi[y0:y1,x0:x1]=True
   bw=(np.all(a==BLACK,2)|np.all(a==WHITE,2))
   if masktype=='enclosed':mask=enclosed_text(a,roi)
   elif masktype=='black':mask=roi&np.all(a==BLACK,2)
   elif masktype=='red':mask=roi&((np.all(a==BLACK,2))|((a[:,:,0]>200)&(a[:,:,1]<160)&(a[:,:,2]<160)&(a[:,:,3]>0)))
   elif masktype=='yellow':mask=roi&(np.all(a==BLACK,2)|((a[:,:,0]>200)&(a[:,:,1]>200)&(a[:,:,2]<150)&(a[:,:,3]>0)))
   elif background=='black':mask=roi&np.all(a==WHITE,2)
   else:mask=roi&bw
   assert mask.any(),(group,box,text)
   for yy,xx in zip(*np.where(mask)):
    if background=='normal':
     if 16<=xx<114 and 40<=yy<136:
      candidates=np.flatnonzero(blue[:,yy,xx]);b[yy,xx]=normal[candidates[0],yy,xx] if len(candidates) else (49,148,255,255)
     else:b[yy,xx]=0
    elif background=='blue':
     candidates=[k for k in range(40,120) if a[yy,k,2]>=230 and a[yy,k,0]<90 and a[yy,k,1]>=70]
     assert candidates,(group,yy)
     same=[k for k in candidates if k%2==xx%2];b[yy,xx]=a[yy,min(same or candidates,key=lambda k:abs(k-xx))]
    elif background=='screen':
     candidates=[k for k in range(28,104) if not mask[yy,k] and a[yy,k,0]>=180 and a[yy,k,1]>=180 and a[yy,k,2]>=180]
     assert candidates,(group,yy)
     same=[k for k in candidates if k%2==xx%2];b[yy,xx]=a[yy,min(same or candidates,key=lambda k:abs(k-xx))]
    elif background=='red':
     candidates=[k for k in range(54,118) if a[yy,k,0]>=240 and a[yy,k,1]<60 and a[yy,k,2]<60]
     assert candidates,(group,yy)
     b[yy,xx]=a[yy,min(candidates,key=lambda k:abs(k-xx))]
    elif background=='white':b[yy,xx]=WHITE
    elif background=='black':b[yy,xx]=BLACK
   x,y=pos;tracking=0
   if maxlines>1:g,lines=lines_image(text,width,style,maxlines)
   else:
    lines=[text];g=title_glyph(text,0) if masktype=='red' else glyph(text,style,0)
    if width and g.width>width:
     tracking=-1;g=title_glyph(text,-1) if masktype=='red' else glyph(text,style,-1)
    assert not width or g.width<=width,(group,text,g.size,width)
   if center:x=x+(width-g.width)//2
   ga=np.array(g)
   if fill is not None:ga[(ga[:,:,3]>0)&np.all(ga[:,:,:3]==255,2)]=nearest(fill);g=Image.fromarray(ga)
   assert x>=0 and y>=0 and x+g.width<=128 and y+g.height<=192,(group,text,g.size,pos)
   # Each template reserves a distinct text area; do not let prose hit price bars.
   if mode=='banner' and maxlines>1:assert y+g.height<=140
   if mode=='bubble' and maxlines>1:assert y+g.height<=147
   allowed|=mask;allowed[y:y+g.height,x:x+g.width]|=ga[:,:,3]>0;draws.append((g,x,y))
   parts.append(dict(text=text,font='Galmuri9' if masktype=='red' else 'Galmuri7',font_px=10 if masktype=='red' else 8,box=box,placement=[x,y],lines=lines,tracking_px=tracking,glyph_size=list(g.size),mask_pixels=int(mask.sum()),background=background))
  if mode=='normal':
   edit((20,17,66,28),'상품 No.',(21,18),'normal',width=46)
   edit((33,31,128,44),spec['title'],(33,32),'normal',fill=(255,49,49,255),width=95,masktype='red')
   edit((96,48,115,59),'마네',(97,49),'normal',fill=YELLOW,width=17,masktype='yellow')
   edit((20,134,128,164),'\n'.join(spec['description_lines']),(21,134),'normal',width=106,maxlines=5)
  elif mode=='banner':
   edit((40,27,119,38),spec['title'],(40,28),'blue',width=78,center=True)
   edit((19,43,64,52),'상품 No.',(20,43),'black',width=45)
   edit((20,108,119,139),'\n'.join(spec['description_lines']),(21,109),'blue',width=98,maxlines=3)
   edit((98,144,117,155),'마네',(99,145),'red',width=17)
  else:
   edit((34,85,84,96),'상품 No.',(36,86),'screen',width=47,masktype='enclosed')
   edit((24,115,112,126),spec['title'],(24,116),'white',style='black_white',width=88,center=True,masktype='black')
   edit((24,127,112,145),'\n'.join(spec['description_lines']),(29,127),'white',style='black_white',width=82,maxlines=2,masktype='black')
   edit((96,150,114,161),'마네',(97,151),'red',width=17)
  for color in np.unique(b.reshape(-1,4),axis=0):
   if not np.any(np.all(source_palette==color,1)):b[np.all(b==color,2)]=nearest(color)
  if mode=='normal':assert not np.any(b[31:40,33:128,3]),(group,'title residue')
  clean=Image.fromarray(b);result=clean.copy()
  for g,x,y in draws:result.alpha_composite(g,(x,y))
  out=np.array(result);assert not np.any(np.any(a!=out,2)&~allowed)
  if mode=='normal':assert np.array_equal(a[59:134],out[59:134]),(group,'product pixels changed')
  palette=set(map(tuple,a.reshape(-1,4)));extra=set(map(tuple,out.reshape(-1,4)))-palette-{(0,0,0,0)}
  assert not extra,(group,extra)
  stem=group+'-cell-0';result.save(OUT/(stem+'-ko.png'));clean.save(OUT/(stem+'-clean.png'))
  notes=['빨간 상품 제목은 갈무리9 10px(글자 높이9px+외곽선). 나머지는 갈무리7 8px. 원본 128×192 유지 · 글자·외곽선 마스크만 제거 · 비문자 픽셀 보존.','상품 그림·색상 견본·아이콘·통화 기호·오렌지사 로고 보존. 설명은 같은 캔버스 안에서 줄바꿈.']
  entries.append(dict(id=group+'/cell/0',group=group,cell=0,source=asset['image'],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),result_image=f'../graphics-draft/cards-bulk-v1/{stem}-ko.png',reading=spec['reading'],translation=spec['title']+' / '+spec['description'],title=spec['title'],description=spec['description'],notes=notes,size=[128,192],stage='draft',font='Galmuri7',font_px=8,title_font='Galmuri9' if mode=='normal' else 'Galmuri7',title_font_px=10 if mode=='normal' else 8,template=mode,checks=dict(parts=parts,nontext_pixels_preserved=True,palette_preserved=True),runtime_verified=False,rom_inserted=False))
 assert len(entries)==68
 (ROOT/'metadata/graphics_cards_bulk_draft_v1.json').write_text(json.dumps(dict(batch='cards-bulk-v1',entries=entries,edited_cells=68,rom_modified=False,runtime_verified=False),ensure_ascii=False,indent=2)+'\n','utf8')
 cards=[]
 for e in entries:
  pairs=[]
  for scale in (1,2):
   pair=''.join(f'<figure><figcaption>{label} · {scale}배</figcaption><div class="checker"><img src="{html.escape(path)}?revision=red-title-galmuri9-v3" width="{128*scale}" height="{192*scale}" alt="{html.escape(e["title"])}"></div></figure>' for label,path in [('원본','../../graphics-review/'+e['source']),('한국어',Path(e['result_image']).name)])
   pairs.append('<div class="pair">'+pair+'</div>')
  cards.append(f'<article id="{e["group"]}-cell-0" data-search="{html.escape(e["title"]+e["description"]+e["group"])}"><h2>{e["group"]} · {html.escape(e["title"])}</h2><p>{html.escape(e["reading"])}</p>{"".join(pairs)}<p>{html.escape(e["description"])}</p></article>')
 page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>홈쇼핑 상품 카드 전체 · 68개</title><style>body{margin:0;background:#edf1e7;color:#172323;font:16px/1.5 sans-serif}main{max-width:1460px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(560px,1fr));gap:16px}article{padding:20px;background:white;border-radius:12px;overflow:auto}article[hidden]{display:none}h2{font-size:19px;margin:0}figure{margin:0}.pair{display:flex;gap:24px;margin:16px 0;align-items:start}figcaption{font-size:13px;color:#586366}.checker{display:inline-block;background:repeating-conic-gradient(#ddd 0% 25%,#fff 0% 50%) 0/8px 8px;line-height:0}img{image-rendering:pixelated}.note{background:white;padding:14px;border-left:4px solid #52745b}input{padding:10px;font:inherit;width:300px;margin-bottom:18px}@media(max-width:620px){.grid{display:block}article{margin-bottom:16px}}</style><main><a href="../../graphics-review/dashboard.html?revision=cards-bulk-v1">← 카테고리 현황판</a><h1>홈쇼핑 상품 카드 전체 · 68개</h1><p>상품명·설명문·상품 번호·가격 단위를 함께 옮겼습니다. 실제 크기와 2배 비교.</p><p class="note">빨간 제목: 갈무리9 · 설명: 갈무리7 · 원본 캔버스 유지 · 상품 그림과 로고 보존. 앞선 경품61개는 검토 승인으로 기록했습니다. 이번68개는 검토용 수정안이며 ROM 반영 전입니다.</p><input id="filter" aria-label="상품명 또는 설명 검색" placeholder="상품명 또는 설명 검색"><span id="count">68개</span><div class="grid">'''+''.join(cards)+'''</div></main><script>document.getElementById('filter').addEventListener('input',e=>{let n=0;for(const a of document.querySelectorAll('article')){a.hidden=!a.dataset.search.includes(e.target.value.trim());if(!a.hidden)n++}document.getElementById('count').textContent=n+'개'});</script></html>'''
 (OUT/'index.html').write_text(page,'utf8')
 for start in range(0,68,12):
  chunk=entries[start:start+12];sheet=Image.new('RGB',(1152,((len(chunk)+3)//4)*410),(215,215,215));d=ImageDraw.Draw(sheet)
  for n,e in enumerate(chunk):
   x=n%4*288;y=n//4*410;d.text((x,y),e['group'],fill='black');im=Image.open(OUT/Path(e['result_image']).name).convert('RGBA').resize((256,384),Image.Resampling.NEAREST);sheet.paste(im,(x,y+20),im)
  sheet.save(OUT/f'qa-{start//12}.png')
 print('68 shopping cards generated and native bounds/palette/masks verified')

if __name__=='__main__':main()
