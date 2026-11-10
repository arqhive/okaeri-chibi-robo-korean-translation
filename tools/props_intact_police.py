"""Recompose T1702 using the intact original T1703 character and existing lettering."""
import numpy as np
from PIL import Image
from scipy.ndimage import label,binary_dilation,binary_fill_holes

def preserve_character_alpha(a,out,source_path,mask_path):
 source=np.array(Image.open(source_path).convert('RGBA'));mask=np.array(Image.open(mask_path))>0
 colors=np.unique(a.reshape(-1,4),axis=0).astype('int32')
 for c in np.unique(source[mask],axis=0):
  candidates=colors[colors[:,3]==int(c[3])]
  assert len(candidates),('missing original alpha',c[3])
  best=candidates[((candidates[:,:3]-c[:3].astype('int32'))**2).sum(1).argmin()]
  out[mask&np.all(source==c,axis=2)]=best
 assert np.array_equal(out[mask,3],source[mask,3])
 return out

def compose(a,q,source_path,output_dir):
 source=np.array(Image.open(source_path).convert('RGBA'))
 labels,_=label(source[:,:,3]>0)
 # The component at (24, 4) includes the complete character, both shoes and AA.
 component=labels[4,24]
 assert component>0
 charmask=labels==component
 ys,xs=np.where(charmask)
 assert (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))==(3,1,43,64)
 b=np.zeros_like(a);b[charmask]=source[charmask]
 yy,xx=np.indices(a.shape[:2]);rgb=q[:,:,:3].astype(int)
 white=(rgb.min(2)>170)&(q[:,:,3]>100)&(xx>=19)&(yy>=18)&(yy<51)
 glyph=binary_fill_holes(binary_dilation(white,iterations=1));outline=binary_dilation(glyph,iterations=1)
 letters=np.zeros_like(a);letters[outline]=[0,0,0,255]
 inside=glyph&(q[:,:,3]>100)&((rgb.min(2)>120)|((rgb[:,:,2]>rgb[:,:,0]*1.3)&(rgb[:,:,2]>rgb[:,:,1]*1.3)))
 letters[inside]=q[inside];letters[inside,3]=255
 ly,lx=np.where(outline);box=(int(lx.min()),int(ly.min()),int(lx.max()+1),int(ly.max()+1))
 resized=np.array(Image.fromarray(letters).crop(box).resize((109,37),Image.Resampling.LANCZOS))
 overlay=np.zeros_like(a);overlay[14:51,18:127]=resized;textmask=overlay[:,:,3]>100
 b[textmask]=overlay[textmask];b[textmask,3]=255
 Image.fromarray(charmask.astype('uint8')*255).save(output_dir/'T1702-character-mask-v6.png')
 Image.fromarray((charmask&~textmask).astype('uint8')*255).save(output_dir/'T1702-visible-character-mask-v6.png')
 Image.fromarray(textmask.astype('uint8')*255).save(output_dir/'T1702-text-mask-v6.png')
 return b,np.any(a!=b,axis=2),textmask
