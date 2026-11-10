"""Composite ImageGen print onto the original poster's restored lettering masks."""
from pathlib import Path
import numpy as np,json
from PIL import Image,ImageFilter
from scipy.ndimage import distance_transform_edt
from draft_ui01_graphics import glyph
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'work/graphics-draft/ui-bulk-v1/poster-imagegen'
def main():
 raw=Image.open(D/'generated-source.png').convert('RGB');s=np.array(raw).astype(int);sx=raw.width/256;sy=raw.height/192
 orig=Image.open(ROOT/'work/scope-review/assets/SubScPrize-cell-0.png').convert('RGBA');a=np.array(orig)
 clean=Image.open(D/'original-background-restored.png').convert('RGBA');b=np.array(clean)
 # Rebuild complete badges from original pixels. The previous partial
 # erasure sampled pale paper colors into the fruit and cut off A/B/C edges.
 orange=[(255,172,0,255),(246,148,24,255)]
 fruit_colors=orange+[(255,197,74,255),(255,213,139,255)]
 yy,xx=np.indices(a.shape[:2])
 for offset in (0,80,160):
  box=(35+offset,79,64+offset,98);x0,y0,x1,y1=box
  b[y0:y1,x0:x1]=a[y0:y1,x0:x1]
  roi=np.zeros(a.shape[:2],bool);roi[y0:y1,x0:x1]=True
  keep=np.zeros_like(roi);candidates=np.zeros_like(roi)
  for c in fruit_colors:keep|=np.all(a==c,2)
  for c in orange:candidates|=np.all(a==c,2)
  nearby=(xx>=x0)&(xx<x1)&(yy>=76)&(yy<105)
  old_letter=roi&~keep
  for py in range(2):
   for px in range(2):
    target=old_letter&(xx%2==px)&(yy%2==py)
    usable=nearby&candidates&~old_letter&(xx%2==px)&(yy%2==py)
    assert usable.any()
    indices=distance_transform_edt(~usable,return_distances=False,return_indices=True)
    b[target]=a[indices[0][target],indices[1][target]]
 clean=Image.fromarray(b);clean.save(D/'repaired-background.png')
 out=clean.copy();allowed=np.any(a!=b,2);parts=[]
 def mask(box,kind):
  x0,y0,x1,y1=box;q=s[round(y0*sy):round(y1*sy),round(x0*sx):round(x1*sx)]
  if kind=='red':m=(q[:,:,0]>160)&(q[:,:,1]<100)&(q[:,:,2]<100)
  elif kind=='white':m=(q.min(2)>230)
  elif kind=='green':m=(q[:,:,1]>q[:,:,0]+15)&(q[:,:,1]>q[:,:,2]+15)
  else:raise ValueError(kind)
  im=Image.fromarray(m.astype('uint8')*255);assert im.getbbox(),box;return im.crop(im.getbbox())
 def place(m,text,xy,size,color,edge=False):
  x,y=xy;w,h=size
  if edge:
   small=m.resize((w-2,h-2),Image.Resampling.LANCZOS);alpha=Image.new('L',size);alpha.paste(small,(1,1))
   g=Image.new('RGBA',size,(90,131,0,0));g.putalpha(alpha.filter(ImageFilter.MaxFilter(3)));f=Image.new('RGBA',size,color);f.putalpha(alpha);g.alpha_composite(f)
  else:g=Image.new('RGBA',size,color);g.putalpha(m.resize(size,Image.Resampling.LANCZOS))
  out.alpha_composite(g,xy);allowed[y:y+h,x:x+w]|=np.array(g)[:,:,3]>0
  parts.append(dict(text=text,placement=list(xy),size=list(size),font='ImageGen'))
 white=(255,255,255,255);green=(90,131,0,255);red=(230,24,32,255)
 place(mask((59,15,226,26),'white'),'올해도 오렌지사가 생활을 업그레이드!',(60,17),(179,7),white)
 place(mask((59,29,208,49),'red'),'당신도 부자로!',(60,30),(139,17),red)
 place(mask((182,49,246,68),'red'),'캠페인',(154,49),(90,15),red)
 place(mask((59,51,131,62),'green'),'응모자 전원 선물',(60,53),(77,8),green)
 for offset,letter in [(0,'A'),(80,'B'),(160,'C')]:
  place(mask((35+offset,81,61+offset,95),'white'),letter+'상',(36+offset,81),(26,14),white,True)
 lines=['치비로보가','너무 열심히','일한 탓에','품절이에요!']
 for x in (20,100,180):
  for n,t in enumerate(lines):
   g=glyph(t,'white_black',0);ga=np.array(g);edge=(ga[:,:,3]>0)&np.all(ga[:,:,:3]==0,2);ga[edge]=green;g=Image.fromarray(ga)
   y=112+n*10;out.alpha_composite(g,(x,y));allowed[y:y+g.height,x:x+g.width]|=ga[:,:,3]>0
   parts.append(dict(text=t,placement=[x,y],size=list(g.size),font='Galmuri7',font_px=8))
 oa=np.array(out);pal=np.unique(a.reshape(-1,4),axis=0).astype(int)
 for c in np.unique(oa.reshape(-1,4),axis=0):
  if not np.any(np.all(pal==c,1)):oa[np.all(oa==c,2)]=pal[np.sum((pal-c.astype(int))**2,1).argmin()]
 assert not np.any(np.any(a!=oa,2)&~allowed)
 Image.fromarray(oa).save(D/'G0230-cell-0-native.png');Image.fromarray(allowed.astype('uint8')*255).save(D/'edit-mask.png')
 (D/'manifest.json').write_text(json.dumps(dict(engine='built-in image_gen',parts=parts,canvas=[256,192],nontext_pixels_preserved=True,palette_preserved=True),ensure_ascii=False,indent=2)+'\n','utf8')
 sheet=Image.new('RGB',(1040,620),'#ddd')
 for n,im in enumerate([orig,Image.fromarray(oa)]):sheet.paste(im,(n*528,0));sheet.paste(im.resize((512,384),Image.Resampling.NEAREST),(n*528,220))
 sheet.save(D/'comparison-qa.png')
 print('Poster lettering prepared at native size.')
if __name__=='__main__':main()
