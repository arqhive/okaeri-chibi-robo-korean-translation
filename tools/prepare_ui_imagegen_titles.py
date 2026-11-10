"""Prepare generated title lettering for the four original DS sprite footprints."""
from pathlib import Path
import shutil,json
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/ui-bulk-v1/imagegen'
FILES=['exec-6cdb0d85-5426-4be7-babe-81bf97a8e693.png','exec-0b8822d7-f592-4579-8f51-6c60d4048ad1.png','exec-a19cfe16-b11a-4861-af4b-000a0a12e800.png','exec-50ad6a65-e883-4b5a-9a1b-90b147343d8d.png']
GENERATED=Path('C:/Users/hgyst/.codex/generated_images/01a13e42-4136-71e0-85ba-dd9c1e92235b')
def main():
 jobs=json.loads((OUT/'prompts.json').read_text('utf8'))['jobs'];records=[]
 sheet=Image.new('RGB',(1050,4*200),'#aaa');dr=ImageDraw.Draw(sheet)
 for n,(j,f) in enumerate(zip(jobs,FILES)):
  src=OUT/(j['id']+'-source.png');shutil.copy2(GENERATED/f,src)
  original=Image.open(ROOT/'work/scope-review/assets'/(j['src']+'.png')).convert('RGBA')
  box=original.crop((0,0,original.width,16)).getbbox();x,y,x2,y2=box;size=(x2-x,y2-y)
  raw=Image.open(src).convert('RGBA');aa=np.array(raw);ys,xs=np.where(aa[:,:,3]>=32);crop=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1));cut=raw.crop(crop)
  pal=np.unique(np.array(original)[:16].reshape(-1,4),axis=0);pal=pal[pal[:,3]>0]
  for col,method in enumerate([Image.Resampling.BOX,Image.Resampling.LANCZOS,Image.Resampling.NEAREST]):
   g=cut.resize(size,method);a=np.array(g);mask=a[:,:,3]>=128;rgb=a[:,:,:3].astype(float);p=pal[:,:3].astype(float)
   idx=np.sum((rgb[:,:,None,:]-p[None,None,:,:])**2,axis=3).argmin(2);a=pal[idx];a[~mask]=0;g=Image.fromarray(a)
   if col==0:g.save(OUT/(j['id']+'-native.png'))
   preview=original.copy();preview.paste((0,0,0,0),(0,0,original.width,16));preview.alpha_composite(g,(x,y))
   px=col*350;py=n*200;dr.text((px,py),j['id']+' '+str(method),fill='black');sheet.paste(preview.resize((original.width*2,original.height*2),Image.Resampling.NEAREST),(px,py+20),preview.resize((original.width*2,original.height*2),Image.Resampling.NEAREST))
   gg=g.resize((g.width*2,g.height*4),Image.Resampling.NEAREST);sheet.paste(gg,(px,py+100),gg)
  records.append(dict(id=j['id'],text=j['text'],source=str(src.relative_to(ROOT)),native=str((OUT/(j['id']+'-native.png')).relative_to(ROOT)),placement=[x,y],size=list(size),crop=crop,palette='original heading opaque colors',sampling='BOX, alpha >= 128',engine='built-in image_gen'))
 (OUT/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8');sheet.save(OUT/'sampling-qa.png')
 print(json.dumps(records,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
