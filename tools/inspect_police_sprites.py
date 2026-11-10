from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
R=Path(__file__).resolve().parents[1];D=R/'work/scope-followup/textures';O=R/'work/graphics-draft/props-bulk-v1/imagegen';rank=[]
for p in D.glob('*.png'):
 a=np.array(Image.open(p).convert('RGBA')).astype(int);r,g,b,al=a.transpose(2,0,1)
 pink=(r>180)&(b>80)&(r>g*1.45)&(al>100)
 blue=(b>150)&(b>r*1.4)&(b>g*1.3)&(al>100)
 if pink.sum()>20 and blue.sum()>20 and (al==0).mean()>.05:rank.append((float(min(pink.mean(),blue.mean())),p))
rank.sort(reverse=True);chosen=rank[:48];sheet=Image.new('RGB',(1000,((len(chosen)+4)//5)*155),'#aaa');d=ImageDraw.Draw(sheet)
for i,(score,p) in enumerate(chosen):
 im=Image.open(p).convert('RGBA');scale=min(190/im.width,125/im.height);im=im.resize((int(im.width*scale),int(im.height*scale)),Image.Resampling.NEAREST);x=(i%5)*200;y=(i//5)*155
 d.text((x,y),p.stem,fill='black');sheet.paste(im,(x,y+20),im)
sheet.save(O/'police-candidates-v4.png')
(O/'police-search-v4.json').write_text(json.dumps(dict(searched_textures=len(list(D.glob('*.png'))),color_candidates=[dict(id=p.stem,score=s) for s,p in rank]),indent=2),'utf8')
print('searched',len(list(D.glob('*.png'))),'candidates',len(rank))
