"""Decode custom texture candidates, recording structural versus inferred settings."""
import json,struct,math,collections
from pathlib import Path
from survey_translation_scope import ROOT,tiles,palette,screen
from survey_scope_followup import grid
import ndspy.color,ndspy.texture
OUT=ROOT/'work/scope-deep'
def main():
 rom=(ROOT/json.loads((ROOT/'metadata/originals.json').read_text())['roms'][0]['file']).read_bytes()
 files={e['path']:rom[e['offset']:e['offset']+e['size']] for e in json.loads((ROOT/'metadata/filesystem_inventory.json').read_text())['entries']}
 a=(ROOT/'work/code/arm9.bin').read_bytes();ndspy.color.prepareLUTs();(OUT/'custom').mkdir(exist_ok=True)
 bpc=collections.defaultdict(set)
 for r in json.loads((ROOT/'metadata/deep_effect_headers.json').read_text()):
  for t in r['textures']:bpc[Path(t['name']).stem.lower()].add(tuple(t['preceding_u32'][-3:]))
 rows=[];errors=[]
 for name,d in files.items():
  if not name.endswith('.ntft'):continue
  p=files[name[:-1]+'p'];colors=list(struct.unpack('<'+'H'*(len(p)//2),p));stem=Path(name).stem
  choices=[(*v,'BMEA_texture_record') for v in sorted(bpc[stem.lower()])]
  if stem.startswith('BtryNum') and stem!='BtryNumBase':
   param=struct.unpack_from('<I',a,0x253f8)[0];assert param==0x6a820000
   choices=[((param>>26)&7,8<<((param>>20)&7),8<<((param>>23)&7),'ARM9_TEXIMAGE_PARAM_020253F8')]
  if not choices and stem.startswith('Dust'):
   off=a.find(name[:-5].encode()+b'\0')
   for j in range(0,len(a)-8,4):
    if a[j:j+4]!=struct.pack('<I',0x2000000+off):continue
    w,h=struct.unpack_from('<HH',a,j+4)
    if w in [16,32,64,128,256,512] and h in [16,32,64,128,256,512] and w*h==len(d)*4:choices.append((2,w,h,'ARM9_name_dimension_table_I2_size'))
  if not choices:
   fmt=6 if len(colors)==1 else 1 if stem=='rainbow2' else 4 if len(colors)>16 else 3 if len(colors)>4 else 2
   pixels=len(d)*({1:1,2:4,3:2,4:1,6:1}[fmt]);w=2**math.ceil(math.log2(math.sqrt(pixels)));h=pixels//w
   choices=[(fmt,w,h,'palette_size_and_aspect_inference')]
  for fmt,w,h,evidence in choices:
   try:
    assert w*h==len(d)*({1:1,2:4,3:2,4:1,6:1}[fmt])
    im=ndspy.texture.renderTextureDataAsImage(d,b'',fmt,w,h,colors,True);path=f'custom/{len(rows):03d}-{stem}.png';im.save(OUT/path)
    rows.append({'file':name,'format':fmt,'width':w,'height':h,'evidence':evidence,'image':path})
   except Exception as ex:errors.append({'file':name,'error':repr(ex)})
 # CmCode: instruction at 020561C8 selects index*128, 020561CC loads128 bytes;
 # 02056388 literal 02056478 supplies TEXIMAGE_PARAM 68A20000 (I2,32x16).
 raw=files['tex/CmCode.ntftp'];p=files['tex/CmCode.ntfpp'];v=struct.unpack_from('<I',a,0x56478)[0];fmt=(v>>26)&7;w=8<<((v>>20)&7);h=8<<((v>>23)&7)
 assert (fmt,w,h)==(2,32,16) and len(raw)==50*128 and len(p)==50*6
 cm=[]
 for i in range(50):
  # Loader passes the palette base, not index*6; all fifty stored palettes are equal.
  assert p[i*6:i*6+6]==p[:6]
  im=ndspy.texture.renderTextureDataAsImage(raw[i*128:(i+1)*128],b'',fmt,w,h,list(struct.unpack('<3H',p[:6])),True)
  path=f'custom/cmcode-{i:02d}.png';im.save(OUT/path);cm.append({'index':i,'image':path})
 grid([(str(r['index']),__import__('PIL').Image.open(OUT/r['image']).resize((128,64),__import__('PIL').Image.Resampling.NEAREST)) for r in cm],OUT/'boards/cmcode.png',cols=5,box=(180,100))
 for i in range(0,len(rows),20):grid([(Path(r['file']).name,__import__('PIL').Image.open(OUT/r['image'])) for r in rows[i:i+20]],OUT/f'boards/custom-{i//20:02d}.png',cols=4,box=(280,230))
 # Orphan map equality check and fullwidth S candidate assembly, never assert runtime binding.
 target=files['2d/SandBGDef.NSCR'];equal=[n for n,d in files.items() if n.endswith('.NSCR') and d==target and n!='2d/SandBGDef.NSCR']
 full='2d/SandBGJnDefＳ';ts,bpp=tiles(files[full+'.NCGR']);pal=palette(files[full+'.NCLR']);sand=[]
 for n in ['2d/SandBGJnDef.NSCR','2d/SandPan.NSCR','2d/SandBGDef.NSCR']:
  try:
   im=screen(files[n],ts,pal,bpp);path='custom/fullwidth-'+Path(n).stem+'.png';im.save(OUT/path);sand.append({'map':n,'image':path,'evidence':'shared_family_inference_only'})
  except Exception as ex:sand.append({'map':n,'error':repr(ex)})
 result={'textures':rows,'errors':errors,'cmcode':cm,'cmcode_evidence':{'texture_param':hex(v),'format':fmt,'width':w,'height':h,'frame_bytes':128,'frame_count':50,'loader':'0x02056174','draw':'0x020561dc'},'orphan_map_equal_to':equal,'fullwidth_s_candidates':sand}
 (ROOT/'metadata/deep_custom_textures.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('textures',len(rows),'errors',errors,'cmcode',len(cm),'evidence',collections.Counter(r['evidence'] for r in rows),'map equal',equal)
if __name__=='__main__':main()
