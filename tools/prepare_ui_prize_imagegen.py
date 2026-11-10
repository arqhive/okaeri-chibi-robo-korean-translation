"""Extract ImageGen Korean print and composite only glyph masks on the original card."""
from pathlib import Path
import json,shutil,hashlib
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/ui-bulk-v1/prize-imagegen'
SOURCE=Path('C:/Users/hgyst/.codex/generated_images/01a13e42-4136-71e0-85ba-dd9c1e92235b/exec-d6ddeb7c-33d4-48f2-a303-107febb65b7b.png')
def main():
 OUT.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE,OUT/'generated-source.png')
 raw=Image.open(SOURCE).convert('RGB');s=np.array(raw).astype(int);sx=raw.width/256;sy=raw.height/192
 orig=Image.open(ROOT/'work/scope-review/assets/MainScPrize-cell-14.png').convert('RGBA');a=np.array(orig);b=a.copy();allowed=np.zeros(a.shape[:2],bool)
 # These ROIs are inside flat source fields; change only pixels that differ
 # from the field, leaving original circle edges, paper and illustration exact.
 boxes=[((34,12,224,22),(255,213,139,255)),((35,95,78,107),(255,255,255,255)),((30,155,224,174),(255,213,139,255))]
 for x,y in [(52,49),(116,49),(180,49),(116,105),(180,105)]:boxes.append(((x-2,y-2,x+29,y+17),(205,205,205,255)))
 for (x0,y0,x1,y1),color in boxes:
  mask=np.zeros(allowed.shape,bool);mask[y0:y1,x0:x1]=np.any(a[y0:y1,x0:x1]!=color,axis=2);b[mask]=color;allowed|=mask
 clean=Image.fromarray(b);out=clean.copy();parts=[]
 def extract(box,white=False):
  x0,y0,x1,y1=box;q=s[round(y0*sy):round(y1*sy),round(x0*sx):round(x1*sx)]
  if white:mask=(q.min(2)>217)&((q.max(2)-q.min(2))<25)
  else:mask=(q[:,:,1]>q[:,:,0]+12)&(q[:,:,1]>q[:,:,2]+20)
  im=Image.fromarray(np.uint8(mask)*255);assert im.getbbox(),box;return im.crop(im.getbbox())
 def place(mask,text,pos,size,white=False):
  mask=mask.resize(size,Image.Resampling.LANCZOS);g=Image.new('RGBA',size,(255,255,255,255) if white else (90,131,0,255));g.putalpha(mask)
  x,y=pos;out.alpha_composite(g,pos);allowed[y:y+size[1],x:x+size[0]]|=np.array(mask)>0;parts.append(dict(text=text,placement=list(pos),size=list(size),font='ImageGen'))
 place(extract((32,11,216,22)),'↓ 안에 응모 스티커 6장을 모아 붙여 주세요',(34,13),(184,8))
 stamp=extract((50,46,79,67),True)
 for cx,cy in [(64,57),(128,57),(192,57),(128,113),(192,113)]:place(stamp,'응모 / 스티커',(cx-14,cy-9),(28,18),True)
 place(extract((39,94,74,109)),'밀기',(36,96),(31,11))
 place(extract((29,154,204,165)),'※ A·B·C상 외에 꽝이 나올 수도 있어요.',(30,156),(187,8))
 place(extract((29,165,198,177)),'※ 경품 발송으로 당첨 발표를 대신해요.',(30,166),(187,8))
 # Original palette only. All compositing changes are limited to old/new ink.
 oa=np.array(out);pal=np.unique(a.reshape(-1,4),axis=0).astype(int)
 for color in np.unique(oa.reshape(-1,4),axis=0):
  if not np.any(np.all(pal==color,1)):oa[np.all(oa==color,2)]=pal[np.sum((pal-color.astype(int))**2,1).argmin()]
 assert not np.any(np.any(a!=oa,2)&~allowed)
 out=Image.fromarray(oa);out.save(OUT/'G0029-cell-14-native.png');clean.save(OUT/'G0029-cell-14-clean.png')
 Image.fromarray(np.uint8(allowed)*255).save(OUT/'edit-mask.png')
 (OUT/'manifest.json').write_text(json.dumps(dict(engine='built-in image_gen',parts=parts,nontext_pixels_preserved=True,palette_preserved=True,canvas=[256,192]),ensure_ascii=False,indent=2)+'\n','utf8')
 sheet=Image.new('RGBA',(1040,450),'#ddd');sheet.alpha_composite(orig.resize((512,384),Image.Resampling.NEAREST),(0,40));sheet.alpha_composite(out.resize((512,384),Image.Resampling.NEAREST),(528,40));sheet.alpha_composite(out,(528,0));sheet.save(OUT/'comparison-qa.png')
 print('ImageGen lettering integrated into original 256x192 card; source artwork preserved.')
if __name__=='__main__':main()
