"""Read-only text inventory and decode local Nitro 2D resources for review."""
from pathlib import Path
import collections, hashlib, html, json, re, struct
import numpy as np
from PIL import Image, ImageDraw
from analyze_text_fonts import blocks,u16,u32
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/scope-review'
SIZES={0:[(8,8),(16,16),(32,32),(64,64)],1:[(16,8),(32,8),(32,16),(64,32)],2:[(8,16),(8,32),(16,32),(32,64)]}


def palette(b):
 o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='TTLP')
 start=o+8+u32(b,o+20);size=u32(b,o+16)
 assert start+size<=o+u32(b,o+4)
 values=np.frombuffer(b[start:start+size],dtype='<u2')
 return np.array([[(v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31,255] for v in values],dtype=np.uint8)


def tiles(b):
 o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='RAHC')
 fmt=u32(b,o+12);assert fmt in (3,4)
 start=o+8+u32(b,o+28);size=u32(b,o+24)
 assert start+size<=o+u32(b,o+4)
 arr=np.frombuffer(b[start:start+size],dtype=np.uint8)
 if fmt==3:arr=np.stack((arr&15,arr>>4),axis=1).reshape(-1)
 assert len(arr)%64==0
 return arr.reshape(-1,8,8),4 if fmt==3 else 8


def rgba(index,pal,bank=0,bpp=8):
 idx=index.astype(np.uint16)+(bank*16 if bpp==4 else 0)
 assert idx.max()<len(pal)
 colors=pal[idx].copy();colors[:,:,3]=np.where(index==0,0,255)
 return Image.fromarray(colors)


def cell_images(b,ts,pal,bpp):
 o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='KBEC')
 count=u16(b,o+8);attr=u16(b,o+10);mapping=u32(b,o+16)
 assert attr==1 and mapping==2 and u32(b,o+20)==0
 table=o+8+u32(b,o+12);oam_base=table+count*16
 result=[]
 for ci in range(count):
  row=table+ci*16;n=u16(b,row);pos=oam_base+u32(b,row+4);objs=[]
  assert pos+6*n<=o+u32(b,o+4)
  for j in range(n):
   a0,a1,a2=struct.unpack_from('<HHH',b,pos+6*j)
   if not(a0&0x100) and a0&0x200:continue
   shape=a0>>14;assert shape in SIZES
   w,h=SIZES[shape][a1>>14];x=a1&511;y=a0&255
   if x>=256:x-=512
   if y>=128:y-=256
   assert bool(a0&0x2000)==(bpp==8)
   tile_start=(a2&1023)*(32<<mapping)//(64 if bpp==8 else 32)
   pixels=np.zeros((h,w),dtype=np.uint8)
   for yy in range(h//8):
    for xx in range(w//8):
     tile=tile_start+yy*(w//8)+xx
     assert tile<len(ts),(ci,j,tile,len(ts))
     pixels[yy*8:yy*8+8,xx*8:xx*8+8]=ts[tile]
   if not(a0&0x100):
    if a1&0x1000:pixels=pixels[:,::-1]
    if a1&0x2000:pixels=pixels[::-1,:]
   objs.append((x,y,rgba(pixels,pal,a2>>12,bpp),bool(a0&0x100)))
  if not objs:
   result.append((Image.new('RGBA',(1,1)),{'index':ci,'empty':True,'object_count':n}));continue
  left=min(x for x,y,im,af in objs);top=min(y for x,y,im,af in objs)
  right=max(x+im.width for x,y,im,af in objs);bottom=max(y+im.height for x,y,im,af in objs)
  assert right-left<=1024 and bottom-top<=1024
  im=Image.new('RGBA',(right-left,bottom-top))
  for x,y,sprite,af in reversed(objs):im.alpha_composite(sprite,(x-left,y-top))
  result.append((im,{'index':ci,'size':list(im.size),'origin':[left,top],'object_count':n,'affine_objects':sum(z[3] for z in objs)}))
 return result


def screen(b,ts,pal,bpp):
 o=next(o for k,o,n in blocks(b,u16(b,12)) if k=='NRCS')
 w,h,mode,kind=struct.unpack_from('<HHHH',b,o+8);size=u32(b,o+16)
 assert kind==0 and size==w*h//32
 data=np.frombuffer(b[o+20:o+20+size],dtype='<u2')
 canvas=Image.new('RGBA',(w,h))
 for y in range(h//8):
  for x in range(w//8):
   block=(y//32)*(w//256)+x//32
   index=block*1024+(y%32)*32+x%32
   value=int(data[index]);tile=value&1023;assert tile<len(ts)
   pixels=ts[tile]
   if value&1024:pixels=pixels[:,::-1]
   if value&2048:pixels=pixels[::-1,:]
   canvas.alpha_composite(rgba(pixels,pal,value>>12,bpp),(x*8,y*8))
 return canvas


def sheet(images,path,width=1100):
 rows=[];x=10;y=12;rowh=0
 for label,im in images:
  if x+im.width+14>width:x=10;y+=rowh+28;rowh=0
  rows.append((x,y,label,im));x+=im.width+14;rowh=max(rowh,im.height)
 height=y+rowh+30;canvas=Image.new('RGB',(width,height),'#e5e6df');draw=ImageDraw.Draw(canvas)
 for x,y,label,im in rows:
  draw.text((x,y),label,fill='black');canvas.paste(im,(x,y+17),im if im.mode=='RGBA' else None)
 canvas.save(path)


def main():
 OUT.mkdir(exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
 inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text(encoding='utf-8'))
 orig=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
 rom=(ROOT/orig['file']).read_bytes();assert hashlib.sha256(rom).hexdigest()==orig['sha256']
 files={x['path']:rom[x['offset']:x['offset']+x['size']] for x in inv['entries']}
 texts=json.loads((ROOT/'metadata/text_entries.json').read_text(encoding='utf-8'))
 groups=collections.defaultdict(list);duplicates=collections.defaultdict(list);tokens=collections.Counter()
 textrows=[]
 for r in texts:
  plain=''.join(t.get('text','') for t in r['parts']);controls=[t['control_hex'] for t in r['parts'] if 'control_hex' in t]
  tokens.update(controls);row=dict(r,plain=plain,placeholders=re.findall(r'%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[dsucfxX]',plain),line_count=len(plain.splitlines()) if plain else 0)
  groups[r['file']].append(row);textrows.append(row)
  if plain:duplicates[json.dumps(r['parts'],ensure_ascii=False,sort_keys=True)].append({'file':r['file'],'index':r['index']})
 summary={'all_entries':len(texts),'text_entries':sum(bool(r['plain']) for r in textrows),'empty_or_control_only':sum(not r['plain'] for r in textrows),
          'unique_nonempty_entries_including_controls':len(duplicates),'duplicate_excess':sum(len(v)-1 for v in duplicates.values()),
          'entries_with_controls':sum(any('control_hex' in x for x in r['parts']) for r in texts),'control_byte_patterns':len(tokens),
          'entries_with_placeholders':sum(bool(r['placeholders']) for r in textrows),'multiline_entries':sum(r['line_count']>1 for r in textrows),
          'files':[{'file':name,'total':len(rows),'nonempty':sum(bool(x['plain']) for x in rows),'with_controls':sum(any('control_hex' in t for t in x['parts']) for x in rows),'with_placeholders':sum(bool(x['placeholders']) for x in rows)} for name,rows in groups.items()],
          'control_patterns':[{'hex':k,'count':v} for k,v in tokens.most_common()],
          'duplicates':[v for v in duplicates.values() if len(v)>1]}
 (ROOT/'metadata/translation_scope_text.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (OUT/'texts.json').write_text(json.dumps(textrows,ensure_ascii=False),encoding='utf-8')
 graphics=[];overview=[]
 for path in sorted(files):
  if not path.endswith('.NCGR'):continue
  stem=path[:-5];name=Path(stem).name;rec={'id':f'G{len(graphics)+1:04d}','stem':stem,'files':[k for k in files if k.rsplit('.',1)[0]==stem],'visual_status':'unreviewed','localization_status':'undecided'}
  try:
   ts,bpp=tiles(files[path]);pal=palette(files[stem+'.NCLR']);rec.update(tiles=len(ts),bpp=bpp,palette_colors=len(pal))
   images=[]
   if stem+'.NCER' in files:
    decoded=cell_images(files[stem+'.NCER'],ts,pal,bpp);rec['kind']='cells';rec['cells']=[info for im,info in decoded]
    for im,info in decoded:
     filename=f'{name}-cell-{info["index"]}.png';im.save(OUT/'assets'/filename);info['image']='assets/'+filename
     images.append((str(info['index']),im))
   elif stem+'.NSCR' in files:
    im=screen(files[stem+'.NSCR'],ts,pal,bpp);rec['kind']='screen';filename=f'{name}-screen.png';im.save(OUT/'assets'/filename);rec['screen_image']='assets/'+filename;images=[('screen',im)]
   else:
    rec['kind']='tile_atlas';canvas=Image.new('RGBA',(256,((len(ts)+31)//32)*8))
    for i,tile in enumerate(ts):canvas.alpha_composite(rgba(tile,pal,0,bpp),((i%32)*8,(i//32)*8))
    filename=f'{name}-tiles.png';canvas.save(OUT/'assets'/filename);rec['atlas_image']='assets/'+filename;images=[('unassembled tiles',canvas)]
   # Preserve native pixels; paginate each cell overview to avoid giant images.
   rec['sheets']=[]
   for batch in range(0,len(images),60):
    filename=f'{name}-sheet-{batch//60}.png';sheet(images[batch:batch+60],OUT/'assets'/filename);rec['sheets'].append('assets/'+filename)
   sample=Image.open(OUT/rec['sheets'][0]).convert('RGBA');sample.thumbnail((350,210),Image.Resampling.NEAREST)
   overview.append((rec['id']+' '+name,sample))
   rec['decode_status']='decoded'
  except Exception as exc:rec.update(decode_status='needs_investigation',error=repr(exc))
  graphics.append(rec)
 for i in range(0,len(overview),12):sheet(overview[i:i+12],OUT/f'overview-{i//12:02d}.png',width=1120)
 report={'source_sha256':orig['sha256'],'groups':graphics,'group_count':len(graphics),'decoded':sum(r['decode_status']=='decoded' for r in graphics),
         'decode_failures':[r for r in graphics if r['decode_status']!='decoded'],
         'scope_note':'Groups are NCGR basenames, not confirmed Japanese-text assets. NCER affine transforms/animation require runtime or NANR evaluation. Raw atlases are not assembled scenes. Model textures and other custom formats are separate pending scope.'}
 (ROOT/'metadata/translation_scope_graphics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('TEXT',json.dumps({k:v for k,v in summary.items() if k not in ['files','duplicates','control_patterns']},ensure_ascii=False))
 print('GRAPHICS',report['group_count'],'decoded',report['decoded'],'errors',[(r['stem'],r['error']) for r in report['decode_failures']])
 print('cells',sum(len(r.get('cells',[])) for r in graphics),'overview sheets',(len(overview)+11)//12)


if __name__=='__main__':main()
