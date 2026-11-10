"""Encode approved PNGs into Nitro 2D resources, with decoded readback checks."""
from pathlib import Path
from collections import Counter,defaultdict
import json,struct,hashlib
import numpy as np
from PIL import Image
from survey_translation_scope import blocks,u16,u32,SIZES,tiles,palette,cell_images,screen
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v02';RES=OUT/'resources';RES.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def save(p,j):(ROOT/p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
def rgba_equal(a,b):return (a[:,:,3]==b[:,:,3])&((a[:,:,3]==0)|np.all(a[:,:,:3]==b[:,:,:3],2))
def decode_indices(indices,pal):
 a=pal[indices].copy();a[:,:,3]=np.where(indices==0,0,255);return a

def encode_png(a,pal,old=None):
 flat=a.reshape(-1,4);uniq,rev=np.unique(flat,axis=0,return_inverse=True);colors=pal[1:].astype(np.int32)
 ds=((uniq[:,None,:3].astype(np.int32)-colors[None,:,:3])**2).sum(2);mapping=(ds.argmin(1)+1).astype(np.uint8);mapping[uniq[:,3]<128]=0
 result=mapping[rev].reshape(a.shape[:2])
 if old is not None:
  eq=rgba_equal(a,decode_indices(old,pal));result[eq]=old[eq]
 return result

def parse_objects(b,ts):
 o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='KBEC');count=u16(b,o+8);table=o+8+u32(b,o+12);base=table+count*16;cells=[]
 assert u16(b,o+10)==1 and u32(b,o+16)==2
 for ci in range(count):
  row=table+ci*16;pos=base+u32(b,row+4);objs=[]
  for z in range(u16(b,row)):
   p=pos+z*6;a0,a1,a2=struct.unpack_from('<HHH',b,p)
   if not a0&256 and a0&512:continue
   w,h=SIZES[a0>>14][a1>>14];x=a1&511;y=a0&255;x=x-512 if x>=256 else x;y=y-256 if y>=128 else y;start=(a2&1023)*2
   raw=ts[start:start+w*h//64].reshape(h//8,w//8,8,8).transpose(0,2,1,3).reshape(h,w).copy();flipx=not(a0&256) and bool(a1&4096);flipy=not(a0&256) and bool(a1&8192)
   if flipx:raw=raw[:,::-1].copy()
   if flipy:raw=raw[::-1].copy()
   objs.append(dict(x=x,y=y,w=w,h=h,start=start,attr_offset=p+4,attr2=a2,pixels=raw,flipx=flipx,flipy=flipy,affine=bool(a0&256),attr0=a0,attr1=a1))
  if objs:
   left=min(t['x'] for t in objs);top=min(t['y'] for t in objs);right=max(t['x']+t['w'] for t in objs);bottom=max(t['y']+t['h'] for t in objs)
  else:left=top=0;right=bottom=1
  cells.append(dict(index=ci,objects=objs,origin=(left,top),size=(right-left,bottom-top)))
 return cells

def raster(c):
 out=np.zeros(c['size'][::-1],np.uint8);left,top=c['origin']
 for t in reversed(c['objects']):
  x=t['x']-left;y=t['y']-top;px=t['pixels'];roi=out[y:y+t['h'],x:x+t['w']];roi[px!=0]=px[px!=0]
 return out

def object_tiles(t):
 a=t['pixels']
 if t['flipy']:a=a[::-1]
 if t['flipx']:a=a[:,::-1]
 return a.reshape(t['h']//8,8,t['w']//8,8).transpose(0,2,1,3).reshape(-1,8,8).copy()

def update_ncgr(b,ts):
 out=bytearray(b);o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='RAHC');start=o+8+u32(b,o+28);oldsize=u32(b,o+24);data=ts.astype(np.uint8).tobytes();diff=len(data)-oldsize
 out[start:start+oldsize]=data;struct.pack_into('<I',out,o+4,u32(b,o+4)+diff);struct.pack_into('<I',out,o+24,len(data));struct.pack_into('<I',out,8,len(out));return bytes(out)

def build_cells(g,assets,files):
 stem=g['stem'];tb=files[stem+'.NCGR'];cb=files[stem+'.NCER'];ts,bpp=tiles(tb);assert bpp==8;pal=palette(files[stem+'.NCLR']);cells=parse_objects(cb,ts);targets={};uncovered=[]
 for a in assets:
  ci=a['cell'];c=cells[ci];orig=raster(c);png=np.array(Image.open(ROOT/'work/graphics-review'/a['result_image']).convert('RGBA'));assert png.shape[:2]==orig.shape
  target=encode_png(png,pal,orig);delta=(orig!=target);yy,xx=np.where(delta);left,top=c['origin']
  # Some approved labels extend into gaps between original sprites. Add only
  # transparent 8x8 coverage there, preserving affine parameters and positions.
  coverage=np.zeros(orig.shape,bool)
  for t in c['objects']:
   ox=t['x']-left;oy=t['y']-top;coverage[oy:oy+t['h'],ox:ox+t['w']]=True
  for hy,hx in zip(*np.where(delta&~coverage)):
   if coverage[hy,hx]:continue
   nx=max(0,min(c['size'][0]-8,int(hx)//8*8));ny=max(0,min(c['size'][1]-8,int(hy)//8*8))
   template=min(c['objects'],key=lambda t:abs(t['x']-left-hx)+abs(t['y']-top-hy))
   a0=(template['attr0']&~0xC0FF)|((ny+top)&255)
   a1=((template['attr1']&0x3E00) if template['affine'] else 0)|((nx+left)&511)
   c['objects'].append(dict(x=nx+left,y=ny+top,w=8,h=8,start=-1,attr_offset=None,attr0=a0,attr1=a1,attr2=template['attr2']&~1023,pixels=np.zeros((8,8),np.uint8),flipx=False,flipy=False,affine=template['affine']))
   coverage[ny:ny+8,nx:nx+8]=True
  for y,x in zip(yy,xx):
   covering=[t for t in c['objects'] if t['x']<=x+left<t['x']+t['w'] and t['y']<=y+top<t['y']+t['h']]
   if not covering:uncovered.append([ci,int(x),int(y)]);continue
   visible=[t for t in covering if t['pixels'][y+top-t['y'],x+left-t['x']]!=0]
   if target[y,x]==0:
    for t in visible:t['pixels'][y+top-t['y'],x+left-t['x']]=0
   else:
    t=visible[0] if visible else covering[0];t['pixels'][y+top-t['y'],x+left-t['x']]=target[y,x]
  if not uncovered:assert np.array_equal(raster(c),target),(g['id'],ci)
  targets[ci]=target
 if uncovered:return None,dict(group=g['id'],error='new glyph outside original OAM coverage',uncovered=uncovered)
 # Build explicit tile constraints for every approved OAM, including unchanged pixels.
 demands=defaultdict(Counter);requests=[]
 for ci in targets:
  for obj in cells[ci]['objects']:
   tt=object_tiles(obj);requests.append((ci,obj,tt))
   for k,t in enumerate(tt):
    if obj['start']>=0:demands[obj['start']+k][t.tobytes()]+=1
 protected=set()
 for c in cells:
  if c['index'] not in targets:
   for obj in c['objects']:protected.update(range(obj['start'],obj['start']+obj['w']*obj['h']//64))
 globalts=ts.copy();conflicts=0
 for index,variants in demands.items():
  conflicts+=len(variants)>1
  if index not in protected:
   key=variants.most_common(1)[0][0];globalts[index]=np.frombuffer(key,np.uint8).reshape(8,8)
 packed=list(globalts);nc=bytearray(cb);clones=[];cache={}
 for ci,obj,tt in requests:
  n=len(tt);key=tt.tobytes();start=obj['start']
  if start>=0 and start+n<=len(packed) and np.array_equal(np.array(packed[start:start+n]),tt):continue
  if key in cache:start=cache[key]
  else:
   start=None
   for k in range(0,len(packed)-n+1,2):
    if np.array_equal(packed[k],tt[0]) and np.array_equal(np.array(packed[k:k+n]),tt):start=k;break
   if start is None:
    if len(packed)%2:packed.append(np.zeros((8,8),np.uint8))
    start=len(packed);packed.extend(tt)
   cache[key]=start
  assert start//2<=1023,(g['id'],'OAM address limit',start)
  obj['assigned_start']=start
  if obj['attr_offset'] is not None:struct.pack_into('<H',nc,obj['attr_offset'],(obj['attr2']&~1023)|(start//2))
  clones.append(dict(cell=ci,old_tile=obj['start'],new_tile=start,tiles=n))
 if len(packed)>2048:return None,dict(group=g['id'],error='VRAM size over128KiB',tiles=len(packed))
 # Append extra OAM records while retaining every existing record and bound.
 extras=sum(t['attr_offset'] is None for c in cells for t in c['objects'])
 if extras:
  o=next(o for k,o,n in blocks(cb,u16(cb,12)) if k=='KBEC');table=o+8+u32(cb,o+12);base=table+len(cells)*16
  oldend=max(base+u32(cb,table+c['index']*16+4)+u16(cb,table+c['index']*16)*6 for c in cells)
  payload=bytearray()
  for c in cells:
   row=table+c['index']*16;n=u16(cb,row);start=base+u32(cb,row+4);extra=[t for t in c['objects'] if t['attr_offset'] is None]
   struct.pack_into('<H',nc,row,n+len(extra));struct.pack_into('<I',nc,row+4,len(payload));payload.extend(nc[start:start+n*6])
   for t in extra:payload.extend(struct.pack('<HHH',t['attr0'],t['attr1'],t['attr2']|(t['assigned_start']//2)))
  delta=len(payload)-(oldend-base);nc[base:oldend]=payload;struct.pack_into('<I',nc,o+4,u32(cb,o+4)+delta);struct.pack_into('<I',nc,8,len(nc))
 newts=np.array(packed,np.uint8)
 # Repack all sprite blocks, including every unapproved original cell, into
 # shared aligned chunks instead of appending beyond the original VRAM budget.
 # Equal palette colors can share a single nontransparent index.
 canonical=np.arange(len(pal),dtype=np.uint8);seen={}
 for pi in range(1,len(pal)):
  key=pal[pi,:3].tobytes();canonical[pi]=seen.setdefault(key,pi)
 for c in cells:
  for obj in c['objects']:obj['pixels']=canonical[obj['pixels']]
 unique={};refs=[]
 for c in cells:
  for obj in c['objects']:
   tt=object_tiles(obj);key=tt.tobytes();unique[key]=tt;refs.append((c['index'],obj,key))
 from pack_obj_tiles import pack
 compact,positions=pack(unique)
 split_objects=0
 if len(compact)>len(ts):
  import copy
  candidates=[]
  options=[(16,8,None),(8,16,None),(8,8,None)]
  if g['id']=='G0025':
   shapes=sorted(set((t['w'],t['h']) for c in cells if c['index'] in targets for t in c['objects'] if not t['affine'] and t['w']*t['h']>64))
   options=[(sw,sh,{wh for k,wh in enumerate(shapes) if mask&(1<<k)}) for sw,sh in [(16,8),(8,16)] for mask in range(1,1<<len(shapes))]
  for sw,sh,selected_shapes in options:
   candidate=copy.deepcopy(cells);added=0
   for c in candidate:
    if c['index'] not in targets:continue
    objs=[]
    for obj in c['objects']:
     if (selected_shapes is not None and (obj['w'],obj['h']) not in selected_shapes) or obj['affine'] or (obj['w']<=sw and obj['h']<=sh) or (g['id']=='G0025' and obj['start']>=0 and np.array_equal(object_tiles(obj),ts[obj['start']:obj['start']+obj['w']*obj['h']//64])):objs.append(obj);continue
     for oy in range(0,obj['h'],sh):
      for ox in range(0,obj['w'],sw):
       t=dict(obj);w=min(sw,obj['w']-ox);h=min(sh,obj['h']-oy)
       shape,size=next((a,b) for a,sizes in SIZES.items() for b,wh in enumerate(sizes) if wh==(w,h))
       t.update(x=obj['x']+ox,y=obj['y']+oy,w=w,h=h,pixels=obj['pixels'][oy:oy+h,ox:ox+w].copy(),flipx=False,flipy=False)
       t['attr0']=(obj['attr0']&~0xC0FF)|(shape<<14)|(t['y']&255)
       t['attr1']=(size<<14)|(t['x']&511)
       objs.append(t)
     added+=obj['w']//sw*obj['h']//sh-1
    c['objects']=objs
   uu={};rr=[]
   for c in candidate:
    for obj in c['objects']:
     tt=object_tiles(obj);key=tt.tobytes();uu[key]=tt;rr.append((c['index'],obj,key))
   cc,pp=pack(uu)
   print("PACK",g["id"],sw,sh,len(cc),selected_shapes,flush=True)
   max_objects=max(len(c['objects']) for c in candidate)
   if len(cc)<=len(ts) and max_objects<=128:candidates.append((sum(len(c['objects']) for c in candidate),candidate,cc,pp,rr))
  if candidates:
   _,cells,compact,positions,refs=min(candidates,key=lambda x:x[0]);split_objects=1
   # Rebuild records after splitting only non-affine sprites. Their displayed
   # rectangles and draw order remain identical, including original bounds.
   nc=bytearray(cb);o=next(o for k,o,n in blocks(cb,u16(cb,12)) if k=='KBEC');table=o+8+u32(cb,o+12);base=table+len(cells)*16
   oldend=max(base+u32(cb,table+c['index']*16+4)+u16(cb,table+c['index']*16)*6 for c in cells);payload=bytearray()
   for c in cells:
    row=table+c['index']*16;struct.pack_into('<H',nc,row,len(c['objects']));struct.pack_into('<I',nc,row+4,len(payload))
    for obj in c['objects']:payload.extend(struct.pack('<HHH',obj['attr0'],obj['attr1'],obj['attr2']))
   delta=len(payload)-(oldend-base);nc[base:oldend]=payload;struct.pack_into('<I',nc,o+4,u32(cb,o+4)+delta);struct.pack_into('<I',nc,8,len(nc))
 # NCER may have expanded above; resolve record offsets against that result.
 no=next(o for k,o,n in blocks(nc,u16(nc,12)) if k=='KBEC');ntable=no+8+u32(nc,no+12);nbase=ntable+len(cells)*16
 slot_by_cell={}
 for ci,obj,key in refs:
  slot=slot_by_cell.get(ci,0);slot_by_cell[ci]=slot+1;start=positions[key]
  # No disabled original records occur in these source resources.
  assert len(cells[ci]['objects'])==u16(nc,ntable+ci*16)
  po=nbase+u32(nc,ntable+ci*16+4)+slot*6+4;v=u16(nc,po);struct.pack_into('<H',nc,po,(v&~1023)|(start//2))
 compact_count=len(compact)
 if compact_count<=len(ts):
  compact.extend(np.zeros((8,8),np.uint8) for _ in range(len(ts)-compact_count));newts=np.array(compact,np.uint8)
 else:return None,dict(group=g['id'],error='compact OBJ over original budget',original_tiles=len(ts),compact_tiles=compact_count)
 newtb=update_ncgr(tb,newts);assert len(newtb)==len(tb);decoded=cell_images(bytes(nc),newts,pal,8);errors=[];quant=[]
 for ci,target in targets.items():
  actual=np.array(decoded[ci][0]);expected=decode_indices(target,pal)
  if not rgba_equal(actual,expected).all():errors.append([ci,int((~rgba_equal(actual,expected)).sum())])
  a=next(a for a in assets if a['cell']==ci);png=np.array(Image.open(ROOT/'work/graphics-review'/a['result_image']).convert('RGBA'));quant.append(dict(cell=ci,palette_adjusted_pixels=int((~rgba_equal(actual,png)).sum())))
 assert not errors,(g['id'],errors)
 propagated=[];olddecoded=cell_images(cb,ts,pal,8)
 for ci,((im,_),(oldim,__ )) in enumerate(zip(decoded,olddecoded)):
  if ci not in targets and not rgba_equal(np.array(im),np.array(oldim)).all():propagated.append(ci)
 assert not propagated,(g['id'],'unapproved cell changed',propagated)
 return {stem+'.NCGR':newtb,stem+'.NCER':bytes(nc)},dict(group=g['id'],approved_cells=sum(a.get('draft_stage')=='approved' for a in assets),game_check_cells=[a['cell'] for a in assets if a.get('draft_stage')!='approved'],encoded_cells=len(targets),original_tiles=len(ts),new_tiles=len(newts),used_tiles=compact_count,original_storage_size_preserved=True,tile_conflicts=conflicts,added_oam_objects=extras,remapped_objects=clones,propagated_cells=propagated,palette_adjustments=quant,decoded_readback_passed=True)

def build_screen(g,a,files):
 stem=g['stem'];tb=files[stem+'.NCGR'];mb=files[stem+'.NSCR'];ts,bpp=tiles(tb);assert bpp==8;pal=palette(files[stem+'.NCLR']);im=screen(mb,ts,pal,8);target=np.array(Image.open(ROOT/'work/graphics-review'/a['result_image']).convert('RGBA'));assert target.shape==np.array(im).shape
 indices=encode_png(target,pal);o=next(o for k,o,n in blocks(mb,u16(mb,12)) if k=='NRCS');w,h=im.size;newtiles=[];out=bytearray(mb);cache={}
 for y in range(h//8):
  for x in range(w//8):
   index=((y//32)*(w//256)+x//32)*1024+(y%32)*32+x%32;off=o+20+index*2;t=indices[y*8:y*8+8,x*8:x*8+8];key=t.tobytes()
   if key in cache:k,flip=cache[key]
   else:
    k=len(newtiles);newtiles.append(t.copy());flip=0
    for view,f in [(t,0),(t[:,::-1],1024),(t[::-1],2048),(t[::-1,::-1],3072)]:cache.setdefault(view.tobytes(),(k,f))
   assert k<len(ts),(g['id'],'original BG allocation exceeded',k,len(ts))
   struct.pack_into('<H',out,off,k|flip)
 used=len(newtiles);newtiles.extend(np.zeros((8,8),np.uint8) for _ in range(len(ts)-used));nt=np.array(newtiles,np.uint8);newtb=update_ncgr(tb,nt);assert len(newtb)==len(tb)
 actual=np.array(screen(bytes(out),nt,pal,8));expected=decode_indices(indices,pal);assert rgba_equal(actual,expected).all(),g['id']
 return {stem+'.NCGR':newtb,stem+'.NSCR':bytes(out)},dict(group=g['id'],approved_screens=1,original_tiles=len(ts),new_tiles=len(nt),used_tiles=used,original_storage_size_preserved=True,palette_adjusted_pixels=int((~rgba_equal(actual,target)).sum()),decoded_readback_passed=True)

def main():
 original=read('metadata/originals.json')['roms'][0];rom=(ROOT/original['file']).read_bytes();assert hashlib.sha256(rom).hexdigest()==original['sha256'];files={r['path']:rom[r['offset']:r['offset']+r['size']] for r in read('metadata/filesystem_inventory.json')['entries']};gs={g['id']:g for g in read('metadata/translation_scope_graphics.json')['groups']};w=read('metadata/graphics_worklist.json');reports=[];errs=[];replaced={}
 for r in w['items']:
  aa=[a for a in r['assets'] if a.get('draft_stage')=='approved' or (r['id']=='G0027' and a.get('cell')==10)]
  if not aa or r['kind']!='2D':continue
  g=gs[r['id']]
  try:
   result,report=build_cells(g,aa,files) if g['kind']=='cells' else build_screen(g,aa[0],files)
   if result is None:errs.append(report);print('DEFER',g['id'],report['error'],flush=True)
   else:
    reports.append(report);replaced.update(result)
    print('OK',g['id'],report['original_tiles'],report['new_tiles'],flush=True)
  except Exception as ex:errs.append(dict(group=g['id'],error=repr(ex)));print('ERROR',g['id'],repr(ex),flush=True)
 for name,data in replaced.items():
  p=RES/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 save('metadata/graphics_2d_build_v02.json',dict(groups=reports,errors=errs,replacements=[dict(file=n,size=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in replaced.items()],rom_modified=False))
 print('GROUPS',len(reports),'ERRORS',len(errs),flush=True)
if __name__=='__main__':main()
