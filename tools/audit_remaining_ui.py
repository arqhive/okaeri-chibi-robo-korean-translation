from pathlib import Path
import json,struct,sys
import numpy as np
sys.path.insert(0,str(Path('tools').resolve()))
from survey_translation_scope import blocks,u16,u32,SIZES,tiles,palette,cell_images
ROOT=Path.cwd()
j=json.loads((ROOT/'metadata/translation_scope_graphics.json').read_text('utf8'))
w=json.loads((ROOT/'metadata/graphics_worklist.json').read_text('utf8'))
rom=(ROOT/json.loads((ROOT/'metadata/originals.json').read_text('utf8'))['roms'][0]['file']).read_bytes()
inv={x['path']:x for x in json.loads((ROOT/'metadata/filesystem_inventory.json').read_text('utf8'))['entries']}
def file(p):
 r=inv[p];return rom[r['offset']:r['offset']+r['size']]
def objects(b,ci,bpp=8):
 o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='KBEC');n=u16(b,o+8);table=o+8+u32(b,o+12);base=table+n*16;row=table+ci*16;pos=base+u32(b,row+4);out=[]
 for z in range(u16(b,row)):
  a0,a1,a2=struct.unpack_from('<HHH',b,pos+z*6)
  if not(a0&256) and a0&512:continue
  width,height=SIZES[a0>>14][a1>>14];x=a1&511;y=a0&255;x=x-512 if x>=256 else x;y=y-256 if y>=128 else y
  start=(a2&1023)*2;ids=np.empty((height,width),int)
  for yy in range(height):
   for xx in range(width):ids[yy,xx]=(start+(yy//8)*(width//8)+xx//8)*64+(yy%8)*8+xx%8
  if not a0&256:
   if a1&4096:ids=ids[:,::-1]
   if a1&8192:ids=ids[::-1]
  out.append((x,y,ids))
 return out
if __name__=='__main__':
 from PIL import Image
 for gid in ['G0022','G0031','G0033','G0025','G0032','G0232']:
  g=next(g for g in j['groups'] if g['id']==gid);r=next(r for r in w['items'] if r['id']==gid);b=file(g['stem']+'.NCER');ts,bpp=tiles(file(g['stem']+'.NCGR'))
  print(gid)
  for a in r['assets']:
   ci=a.get('cell')
   if not a.get('result_image') or gid=='G0033':
    obs=objects(b,ci);print(ci,[(x,y,ids.shape, int(ids.min()//64),int(ids.max()//64)) for x,y,ids in obs])
