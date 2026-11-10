"""Read-only static evidence for Sand shared maps; no ROM patching."""
import json,struct,hashlib
from pathlib import Path
import capstone
from survey_translation_scope import ROOT,tiles,palette,screen

def main():
 out=ROOT/'work/scope-followup';(out/'linked-backgrounds').mkdir(exist_ok=True)
 a=(ROOT/'work/code/arm9.bin').read_bytes();b=(ROOT/'work/code/overlay-043.bin').read_bytes();base=0x225a440
 u32=lambda raw,off:struct.unpack_from('<I',raw,off)[0]
 def cstr(raw,off):return raw[off:raw.index(0,off)].decode('ascii')
 # Verify loader object member order from constructor vtables and extension getters.
 extensions=[]
 for off in (0xe650,0xe658,0xe660):
  vt=u32(a,off);fn=u32(a,vt-0x2000000+16)
  extensions.append(cstr(a,u32(a,fn-0x2000000+8)-0x2000000))
 assert extensions==['NCLR','NCGR','NSCR']
 assert cstr(b,0x5548)=='S' and cstr(b,0x554c)=='2d/SandPan'
 table=[];stems={'2d/SandBG'}
 for i in range(9):
  vals=struct.unpack_from('<12I',b,0x225f5d4-base+i*48)
  names=[cstr(b,v-base) if base<=v<base+len(b) else None for v in vals[7:]]
  stems.update(v for v in names if v)
  table.append({'selector':vals[0],'conditions':list(vals[1:7]),'stems':names})
 inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text(encoding='utf-8'))
 original=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
 rom=(ROOT/original['file']).read_bytes();assert hashlib.sha256(rom).hexdigest()==original['sha256']
 files={e['path']:rom[e['offset']:e['offset']+e['size']] for e in inv['entries']}
 rows=[]
 for stem in sorted(stems):
  for suffix in ('','S'):
   name=stem+suffix;ts,bpp=tiles(files[name+'.NCGR']);pal=palette(files[name+'.NCLR'])
   for mapstem in (stem,'2d/SandPan'):
    im=screen(files[mapstem+'.NSCR'],ts,pal,bpp)
    path='linked-backgrounds/'+Path(name).name+'--'+Path(mapstem).name+'.png';im.save(out/path)
    rows.append({'tiles':name+'.NCGR','palette':name+'.NCLR','map':mapstem+'.NSCR','image':path,'evidence':'static_loader_arguments','runtime_verified':False})
 md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM)
 dis=[]
 for raw,ba,lo,hi in [(b,base,0x225bcc0,0x225be20),(a,0x2000000,0x200e5d0,0x200e644),(a,0x2000000,0x200e72c,0x200e7e8),(a,0x2000000,0x200eb2c,0x200eb68)]:
  dis.extend(f'{x.address:08X}  {x.mnemonic} {x.op_str}' for x in md.disasm(raw[lo-ba:hi-ba],lo));dis.append('')
 (out/'sand-code-trace.txt').write_text('\n'.join(dis),encoding='utf-8')
 full='2d/SandBGJnDefＳ';half='2d/SandBGJnDefS'
 result={'source_sha256':original['sha256'],'overlay_base':hex(base),'overlay_sha256':hashlib.sha256(b).hexdigest(),'arm9_sha256':hashlib.sha256(a).hexdigest(),
  'loader':hex(0x200e72c),'loader_arguments':extensions,'table_address':hex(0x225f5d4),'table':table,'stems':sorted(stems),'connections':rows,
  'atlas_connections_resolved_statically':31,'runtime_verified':False,
  'unresolved':['2d/SandBGDef.NSCR',full+'.NCGR'],
  'fullwidth_S_equal_to_ascii_S':{ext:files[full+ext]==files[half+ext] for ext in ('.NCGR','.NCLR')},
  'explanation':'Overlay 43 selects r4 from the 9-row table or SandBG fallback. It copies r4 and conditionally appends ASCII S. At 0225BDB8 loader receives (suffixed,suffixed,r4); at 0225BDF0 it receives (suffixed,suffixed,SandPan). ARM9 constructor vtables prove NCLR/NCGR/NSCR argument order. Conditional paths have not been exercised in the game.'}
 (ROOT/'metadata/scope_code_links.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('static stems',len(stems),'rendered connections',len(rows),'fullwidth duplicate',result['fullwidth_S_equal_to_ascii_S'])

if __name__=='__main__':main()
