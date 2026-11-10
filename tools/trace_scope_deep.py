"""Read-only structural follow-up. Never writes ROM data."""
from pathlib import Path
import json,struct,collections,re,hashlib
from survey_translation_scope import ROOT
from survey_scope_deep import blocks,info,U16,U32
from survey_scope_followup import grid
from PIL import Image
import ndspy.color,ndspy.texture
from ndspy.model import NSBMD

OUT=ROOT/'work/scope-deep'
def save(n,obj): (ROOT/'metadata'/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 original=json.loads((ROOT/'metadata/originals.json').read_text())['roms'][0]
 rom=(ROOT/original['file']).read_bytes();assert hashlib.sha256(rom).hexdigest()==original['sha256']
 inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text());files={e['path']:rom[e['offset']:e['offset']+e['size']] for e in inv['entries']}
 # NANR sequence/frame pointers are relative to their respective banks.
 anim=[];errors=[]
 for name,d in files.items():
  if not name.lower().endswith('.nanr'):continue
  try:
   o=16;assert d[o:o+4]==b'KNBA';end=o+U32(d,o+4);n,nf=struct.unpack_from('<HH',d,o+8)
   so,fo,co=struct.unpack_from('<III',d,o+12);so+=o+8;fo+=o+8;co+=o+8
   cd=files[name[:-5]+'.NCER'];nc=U16(cd,24);seq=[];refs=set();frames=0
   for si in range(n):
    ns,start,typ,mode,fp=struct.unpack_from('<HHIII',d,so+si*16);assert typ>>16==1 and typ&65535 in (0,1,2)
    fr=[]
    for fi in range(ns):
     p=fo+fp+fi*8;assert p+8<=co
     cp,dur,pad=struct.unpack_from('<IHH',d,p);q=co+cp;kind=typ&65535;size={0:2,1:16,2:8}[kind];assert q+size<=end
     cid=U16(d,q);assert cid<nc;refs.add(cid);f={'cell':cid,'duration':dur}
     if kind==1:f.update(rotation=U16(d,q+2),scale=list(struct.unpack_from('<ii',d,q+4)),translation=list(struct.unpack_from('<hh',d,q+12)))
     elif kind==2:f['translation']=list(struct.unpack_from('<hh',d,q+4))
     fr.append(f)
    frames+=ns;seq.append({'index':si,'start':start,'type':typ&65535,'mode':mode,'frames':fr})
   assert frames==nf
   anim.append({'file':name,'cell_count':nc,'referenced_cells':sorted(refs),'unreferenced_cells':sorted(set(range(nc))-refs),'sequences':seq})
  except Exception as ex:errors.append({'file':name,'error':repr(ex)})
 save('deep_animation_links.json',{'files':anim,'errors':errors,'limitation':'Frame-to-cell references verified structurally. A sequence reference does not prove runtime use; cell affine OAM matrices are not reconstructed.'})
 # Exact-name palette inference for the eight model textures lacking static/PAT0 links.
 ndspy.color.prepareLUTs();d=files['mdl/house_gamen.nsbmd'];bs=dict(blocks(d));tx=bs[b'TEX0'];m=NSBMD();m._parseTEX0(tx);ps=dict(m.palettes)
 missing=json.loads((ROOT/'metadata/scope_deep.json').read_text())['unbound_textures'];ims=[];rows=[]
 for r in missing:
  tn=r['texture'];t=dict(m.textures)[tn];pn=r['exact_palette_name_candidate'];p=ps[pn]
  im=ndspy.texture.renderTextureDataAsImage(t.data1,t.data2,t.format,t.width,t.height,[ndspy.color.pack(*c) for c in p.colors],t.isColor0Transparent)
  path='textures/inferred-'+tn+'.png';im.save(OUT/path);ims.append((tn,im));rows.append({'texture':tn,'palette':pn,'image':path,'evidence':'exact_name_inference_only','runtime_verified':False})
 grid(ims,OUT/'boards/inferred-model.png',cols=4,box=(280,280))
 save('deep_inferred_textures.json',rows)
 # BMEA effect headers preserve texture names and dimensions. Collect references conservatively.
 bpcs=[]
 for name,d in files.items():
  if not name.endswith('.bpc'):continue
  hits=[]
  for match in re.finditer(rb'[A-Za-z0-9_\-]+\.tga\x00',d):
   p=match.start();vals=list(struct.unpack_from('<6I',d,p-24)) if p>=24 else []
   hits.append({'offset':p,'name':match.group()[:-1].decode(),'preceding_u32':vals})
  bpcs.append({'file':name,'magic':d[:4].decode('ascii','replace'),'size':len(d),'header_size_matches':U32(d,8)==len(d),'textures':hits})
 save('deep_effect_headers.json',bpcs)
 # Address references across ARM9 and all overlays; references are evidence, not executed paths.
 cr=json.loads((ROOT/'metadata/code_resources.json').read_text());code=[('arm9',0x2000000,(ROOT/'work/code/arm9.bin').read_bytes())]+[(f"overlay-{o['id']:03d}",o['ram_address'],(ROOT/f"work/code/overlay-{o['id']:03d}.bin").read_bytes()) for o in cr['overlays']]
 refs=collections.defaultdict(list)
 for name,base,d in code:
  for off in range(0,len(d)-3,4):
   v=U32(d,off)
   if 0x2000000<=v<0x2400000:refs[v].append({'file':name,'address':hex(base+off)})
 candidates=[]
 def valid(s):
  return len(s)>=2 and sum('\u3040'<=c<='\u30ff' for c in s)>=2 and all(c.isprintable() or c in '\r\n\t' for c in s)
 for name,base,d in code:
  for addr,rr in refs.items():
   off=addr-base
   if not 0<=off<len(d):continue
   rr=[r for r in rr if name=='arm9' or r['file']==name or r['file']=='arm9']
   if not rr:continue
   for enc in ('cp932','utf-16le'):
    if enc=='cp932':
     end=d.find(b'\0',off,off+513)
    else:
     end=next((i for i in range(off,min(len(d)-1,off+1024),2) if d[i:i+2]==b'\0\0'),-1)
    if end<off+2:continue
    try:s=d[off:end].decode(enc)
    except UnicodeError:continue
    if enc=='cp932' and off>0 and d[off-1]!=0:continue
    if enc=='utf-16le' and sum('\u3040'<=c<='\u30ff' for c in s)<len(s)*.2:continue
    if valid(s):candidates.append({'file':name,'address':hex(addr),'offset':off,'encoding':enc,'text':s,'references':rr})
 save('deep_code_string_candidates.json',candidates)
 # Preserve raw disassembly of resource loaders for follow-up.
 import capstone
 md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM);a=code[0][2];lines=[]
 for lo,hi in [(0x4100,0x42b0),(0xf800,0xfb00),(0x3f9c0,0x3fbd0)]:
  lines.extend(f'{x.address:08X} {x.mnemonic} {x.op_str}' for x in md.disasm(a[lo:hi],0x2000000+lo))
 (OUT/'custom-resource-code.txt').write_text('\n'.join(lines),encoding='utf-8')
 targets={s:[] for s in ['tex/CmCode.ntftp','tex/CmCode.ntfpp','house_gamen']}
 for s in targets:
  off=a.find(s.encode()+b'\0');targets[s]={'address':hex(0x2000000+off),'references':refs[0x2000000+off]}
 save('deep_custom_resource_refs.json',targets)
 print('NANR',len(anim),'errors',errors[:3],'BPC',len(bpcs),'strings',len(candidates),'resource refs',targets)

if __name__=='__main__':main()
