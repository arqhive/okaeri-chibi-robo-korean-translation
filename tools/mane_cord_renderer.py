"""Shared native renderer for the 18 Mane price cords; no cord sampling/painting."""
import numpy as np
from PIL import Image
from draft_ui01_graphics import glyph
def render_mane_cord(im,variant,top=7):
 a=np.array(im.convert('RGBA'));b=a.copy();x=35+9*variant;line_y=top+7
 oldmask=np.zeros(a.shape[:2],bool)
 oldmask[top:line_y,x:x+19]=a[top:line_y,x:x+19,3]>0
 b[oldmask]=0
 # Only the Japanese lower strokes protrude into the white area.
 # Plug begins farther right; none of its edge or shadow may be touched.
 foot=np.zeros_like(oldmask);foot[line_y:line_y+2,x:x+14]=True
 foot&=np.all(a==[0,0,0,255],axis=2)
 b[foot]=[255,255,255,255];oldmask|=foot
 clean=Image.fromarray(b);result=clean.copy();g=glyph('마네','white_black',0);y=line_y-g.height+1
 result.alpha_composite(g,(x,y));newmask=np.zeros_like(oldmask);newmask[y:y+g.height,x:x+g.width]=np.array(g)[:,:,3]>0
 # The glyph's bottom row now occupies the white margin above the cord.
 # Protect every lower row and all nonwhite artwork on that margin row.
 oa=np.array(result);protected=np.zeros_like(oldmask);protected[line_y+1:]=True
 protected[line_y]=(~np.all(a[line_y]==[255,255,255,255],axis=1))&(a[line_y,:,3]>0)
 protected&=~foot
 assert np.array_equal(oa[protected],a[protected])
 assert np.array_equal(oa[:,:16],a[:,:16])
 assert not np.any(np.any(oa!=a,2)&~(oldmask|newmask))
 assert set(map(tuple,oa.reshape(-1,4)))<=set(map(tuple,a.reshape(-1,4)))|{(0,0,0,0)}
 check=dict(text='마네',font='Galmuri7',font_px=8,placement=[x,y],size=list(g.size),original_text_top=top,cord_top=line_y,cord_and_plug_pixels_preserved=True,coin_pixels_preserved=True,protected_cord_pixels=int(protected.sum()))
 check.update(tracking_px=0,original_start=[x,y],glyph_bounds=[x,y,x+g.width,y+g.height],box=[x,top,x+19,top+9],background='transparent above intact original cord')
 return result,clean,oldmask|newmask,check
