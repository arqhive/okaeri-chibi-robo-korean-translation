"""Further read-only texture decoding, including shared palettes and PAT0 frames."""
from pathlib import Path
import json,struct,hashlib,collections
import ndspy.color,ndspy.texture
from ndspy.model import NSBMD
from PIL import Image
from survey_translation_scope import ROOT
from survey_scope_followup import grid
OUT=ROOT/'work/scope-deep'
U16=lambda d,o:struct.unpack_from('<H',d,o)[0]
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]

def info(d,o,entrylen):
 count=d[o+1];size=U16(d,o+2);assert o+size<=len(d)
 assert U16(d,o+4)==8 and U16(d,o+6)==12+4*count
 ent=o+12+4*count;each,total=struct.unpack_from('<HH',d,ent)
 assert each==entrylen and total==4+each*count
 names=ent+4+each*count;assert names+16*count<=o+size
 return [(d[names+i*16:names+(i+1)*16].rstrip(b'\0').decode('latin1'),d[ent+4+i*each:ent+4+(i+1)*each]) for i in range(count)]

def blocks(d):
 for off in struct.unpack_from('<'+str(U16(d,14))+'I',d,16):
  b=d[off:off+U32(d,off+4)];assert len(b)==U32(b,4);yield b[:4],b

def materials(d):
 pairs=set();names=set();empty=[]
 for mn,v in info(d,8,4):
  mo=U32(v,0);ma=mo+U32(d,mo+8);to,po=struct.unpack_from('<HH',d,ma)
  mats=info(d,ma+4,4);names.update(n for n,v in mats)
  by=collections.defaultdict(lambda:[set(),set()])
  for k,o in enumerate((to,po)):
   if not d[ma+o+1]:empty.append({'model':mn,'kind':k,'root_value':U32(d,ma+o+8)})
   for n,v in info(d,ma+o,4):
    ptr,num=struct.unpack_from('<HB',v);assert ma+ptr+num<=len(d)
    for mid in d[ma+ptr:ma+ptr+num]:
     assert mid<len(mats);by[mid][k].add(n)
  for tx,pa in by.values():pairs.update((t,p) for t in tx for p in pa)
 return pairs,names,empty

def pat(d,file):
 rows=[]
 for tag,b in blocks(d):
  if tag!=b'PAT0':continue
  for anim,v in info(b,8,4):
   off=U32(v,0);a=b[off:];assert a[:4]==b'M\0PT'
   frames,nt,np,to,po=struct.unpack_from('<HBBHH',a,4)
   def names(start,count):
    assert start+16*count<=len(a)
    return [a[start+i*16:start+(i+1)*16].rstrip(b'\0').decode('latin1') for i in range(count)]
   ts,ps=names(to,nt),names(po,np)
   for mat,v in info(a,12,8):
    n=U16(v,0);ptr=U16(v,6);assert ptr+n*4<=len(a)
    for i in range(n):
     frame,ti,pi=struct.unpack_from('<HBB',a,ptr+i*4);assert ti<nt and pi<np and frame<frames
     rows.append({'file':file,'animation':anim,'material':mat,'frame':frame,'texture':ts[ti],'palette':ps[pi]})
 return rows

def main():
 OUT.mkdir(exist_ok=True)
 for n in ['textures','boards']:(OUT/n).mkdir(exist_ok=True)
 ndspy.color.prepareLUTs()
 original=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
 rom=(ROOT/original['file']).read_bytes();assert hashlib.sha256(rom).hexdigest()==original['sha256']
 inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text(encoding='utf-8'))
 files={e['path']:rom[e['offset']:e['offset']+e['size']] for e in inv['entries']}
 animations=[];animerrors=[]
 for n,d in files.items():
  if not n.endswith('.nsbtp'):continue
  try:animations+=pat(d,n)
  except Exception as ex:animerrors.append({'file':n,'error':repr(ex)})
 bytex=collections.defaultdict(list)
 for a in animations:bytex[a['texture']].append(a)
 old=json.loads((ROOT/'metadata/scope_followup.json').read_text(encoding='utf-8'))
 rows=[dict(r,image='../scope-followup/'+r['image'],deep_occurrences=[]) for r in old['textures']]
 byhash={r['rgba_sha256']:r for r in rows};newcount=0;fail=[];unbound=[];shared=[];empty=[];stats=collections.Counter()
 for n,d in files.items():
  if not n.endswith('.nsbmd'):continue
  try:
   bs=dict(blocks(d))
   if b'TEX0' not in bs:continue
   tx=bs[b'TEX0'];m=NSBMD();m._parseTEX0(tx)
   pairs,matnames,es=materials(bs[b'MDL0']);empty.extend(dict(e,file=n) for e in es)
   paloff,palbase=struct.unpack_from('<II',tx,0x34);pallen=U16(tx,0x30)*8
   pd={name:U16(v,0)*8 for name,v in info(tx,paloff,4)}
   offsets=sorted(set(pd.values())|{pallen});ps={}
   for name,off in pd.items():
    end=next(x for x in offsets if x>off);assert palbase+end<=len(tx)
    ps[name]=list(struct.unpack('<'+str((end-off)//2)+'H',tx[palbase+off:palbase+end]))
   for name,p in m.palettes:
    if not p.colors:shared.append({'file':n,'palette':name,'offset':pd[name],'decoded_colors':len(ps[name]),'reason':'duplicate palette offsets incorrectly yielded empty slice in previous decoder'})
   for tn,t in m.textures:
    chosen={pn:('material',[]) for tt,pn in pairs if tt==tn and pn in ps}
    if int(t.format)==7:chosen={None:('direct',[])}
    if not chosen:
     matches=[a for a in bytex[tn] if a['palette'] in ps and a['material'] in matnames]
     for pn in sorted({a['palette'] for a in matches}):chosen[pn]=('PAT0_name_and_material_compatible',[a for a in matches if a['palette']==pn])
    if not chosen:
     unbound.append({'file':n,'texture':tn,'material_names':sorted(matnames),'palettes':list(ps),'exact_palette_name_candidate':tn+'_pl' if tn+'_pl' in ps else None});continue
    for pn,(kind,ev) in chosen.items():
     try:
      im=ndspy.texture.renderTextureDataAsImage(t.data1,t.data2,t.format,t.width,t.height,ps[pn] if pn else None,t.isColor0Transparent).convert('RGBA')
      key=hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest();stats[kind]+=1
      occurrence={'file':n,'texture':tn,'palette':pn,'association':kind,'animations':ev,'runtime_verified':False}
      if key not in byhash:
       newcount+=1;uid=f'D{newcount:04d}';path='textures/'+uid+'.png';im.save(OUT/path)
       r={'id':uid,'image':path,'width':im.width,'height':im.height,'rgba_sha256':key,'format':int(t.format),'occurrences':[occurrence],'deep_occurrences':[],'visual_status':'unreviewed','localization_status':'unreviewed'}
       rows.append(r);byhash[key]=r
      byhash[key]['deep_occurrences'].append(occurrence)
     except Exception as ex:fail.append({'file':n,'texture':tn,'palette':pn,'error':repr(ex)})
  except Exception as ex:fail.append({'file':n,'error':repr(ex)})
 for i in range(0,newcount,30):
  subset=rows[len(old['textures'])+i:len(old['textures'])+i+30]
  grid([(r['id']+' '+r['occurrences'][0]['texture'],Image.open(OUT/r['image'])) for r in subset],OUT/'boards'/f'recovered-{i//30:02d}.png')
 report={'source_sha256':original['sha256'],'textures':rows,'new_unique_images':newcount,'total_unique_images':len(rows),'rendered_pairs_by_evidence':dict(stats),'rendering_errors':fail,'shared_palette_fixes':shared,'empty_dictionaries':empty,'animation_frames':animations,'animation_parse_errors':animerrors,'unbound_textures':unbound,'limits':'PAT0 frames pair textures/palettes explicitly. Matching model names and material names proves compatibility, not which animation the game uses for that model.'}
 (ROOT/'metadata/scope_deep.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print({k:len(v) if isinstance(v,list) else v for k,v in report.items() if k not in ['textures','source_sha256','limits']})

if __name__=='__main__':main()
