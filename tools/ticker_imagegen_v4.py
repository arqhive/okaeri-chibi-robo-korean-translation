"""Adapt built-in ImageGen ticker lettering to native PNG resources."""
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'work/graphics-draft/final-ui-v1/imagegen'
def composite_ticker(background,left):
 filename='shipping-generated-v4.png' if left==129 else 'phone-generated-v4.png'
 im=Image.open(DIR/filename).convert('RGB');rgb=np.array(im).astype(float)
 # Warm chroma isolates generated lettering, excluding the background and bars.
 alpha=np.clip((rgb[:,:,0]-rgb[:,:,2])/255,0,1)
 alpha[(rgb[:,:,0]<180)|(rgb[:,:,1]>rgb[:,:,0])]=0
 mask=alpha>.12;ys,xs=np.where(mask);box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
 recovered=np.full((*alpha.shape,4),255,dtype=np.uint8)
 recovered[:,:,1]=np.clip(255-(255-rgb[:,:,1])/np.maximum(alpha,.001),0,255).astype(np.uint8)
 recovered[:,:,2]=0;recovered[:,:,3]=np.uint8(alpha*255)
 glyph=Image.fromarray(recovered).crop(box)
 h=8;w=round(glyph.width*h/glyph.height);assert w<202,(filename,w)
 glyph=glyph.resize((w,h),Image.Resampling.LANCZOS)
 ga=np.array(glyph);ga[:,:,3][ga[:,:,3]<24]=0;glyph=Image.fromarray(ga)
 x=55 if left==129 else 90;y=1
 result=Image.fromarray(background.copy());result.alpha_composite(glyph,(x,y));b=np.array(result)
 # Quantize only generated letter pixels to the original ticker palette.
 mask=np.zeros(background.shape[:2],bool);mask[y:y+h,x:x+w]=ga[:,:,3]>0
 original=Image.open(ROOT/f'work/graphics-draft/final-ui-v1/view-{2 if left==129 else 3}-original.png').convert('RGBA')
 pal=np.unique(np.array(original).reshape(-1,4),axis=0).astype(np.int32)
 pix=b[mask].astype(np.int32);dist=((pix[:,None]-pal[None])**2).sum(2);b[mask]=pal[dist.argmin(1)].astype(np.uint8)
 assert np.array_equal(b[~mask],background[~mask])
 assert np.array_equal(b[9:],background[9:])
 return b,mask,dict(generated_source=filename,generated_crop=list(box),placement=[x,y],native_size=[w,h],method='built-in imagegen lettering; original background preserved; native palette')
