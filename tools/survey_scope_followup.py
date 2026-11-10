from pathlib import Path
import collections,hashlib,json,re,struct
import numpy as np
from PIL import Image,ImageDraw
from ndspy.model import NSBMD
import ndspy.color
import ndspy.texture
from ndspy._common import loadInfoBlock
from survey_translation_scope import ROOT,tiles,palette,screen
OUT=ROOT/'work/scope-followup'


def digest(b):return hashlib.sha256(b).hexdigest()


def grid(items,path,cols=6,box=(180,220)):
 w,h=box;canvas=Image.new('RGB',(cols*w,((len(items)+cols-1)//cols)*h),'#e7e8e1');d=ImageDraw.Draw(canvas)
 for i,(label,im) in enumerate(items):
  im=im.copy();im.thumbnail((w-10,h-32),Image.Resampling.NEAREST)
  x=(i%cols)*w+5;y=(i//cols)*h+5;d.text((x,y),label[:27],fill='black')
  canvas.paste(im,(x,y+24),im if im.mode=='RGBA' else None)
 canvas.save(path)


def model_pairs(data):
 pairs=set()
 for model,_,__,entry in loadInfoBlock(data,8,4):
  mo=struct.unpack('<I',entry)[0];ma=mo+struct.unpack_from('<I',data,mo+8)[0]
  texoff,paloff=struct.unpack_from('<HH',data,ma)
  bymaterial=collections.defaultdict(lambda:[set(),set()])
  for k,off in enumerate((texoff,paloff)):
   for name,_,__,value in loadInfoBlock(data,ma+off,4):
    ptr,count=struct.unpack_from('<HB',value)
    for matid in data[ma+ptr:ma+ptr+count]:bymaterial[matid][k].add(name)
  for textures,palettes in bymaterial.values():
   for t in textures:
    for p in palettes:pairs.add((t,p))
 return pairs


def main():
 ndspy.color.prepareLUTs()
 OUT.mkdir(exist_ok=True)
 for name in ['textures','boards','backgrounds']:(OUT/name).mkdir(exist_ok=True)
 inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text(encoding='utf-8'))
 original=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
 rom=(ROOT/original['file']).read_bytes();assert digest(rom)==original['sha256']
 files={e['path']:rom[e['offset']:e['offset']+e['size']] for e in inv['entries']}
 unique={};failures=[];unbound=[];pair_count=0
 for name,data in files.items():
  if not name.endswith('.nsbmd'):continue
  tex=None;mdl=None
  try:
   for off in struct.unpack_from('<'+str(struct.unpack_from('<H',data,14)[0])+'I',data,16):
    block=data[off:off+struct.unpack_from('<I',data,off+4)[0]]
    if block[:4]==b'TEX0':tex=block
    if block[:4]==b'MDL0':mdl=block
   if tex is None:continue
   m=NSBMD();m._parseTEX0(tex);ts=dict(m.textures);ps=dict(m.palettes)
   pairs=model_pairs(mdl) if mdl is not None else set()
   for tn,t in m.textures:
    chosen=[pn for tt,pn in pairs if tt==tn and pn in ps]
    if int(t.format)==7:chosen=[None]
    if not chosen:
     unbound.append({'file':name,'texture':tn,'available_palettes':list(ps)})
     continue
    for pn in sorted(chosen,key=str):
     packed=[ndspy.color.pack(*c) for c in ps[pn].colors] if pn else None
     im=ndspy.texture.renderTextureDataAsImage(t.data1,t.data2,t.format,t.width,t.height,packed,t.isColor0Transparent).convert('RGBA');pair_count+=1
     key=digest(struct.pack('<II',*im.size)+im.tobytes())
     occurrence={'file':name,'texture':tn,'palette':pn,'association':'MDL0 shared material index' if pn else 'direct color'}
     if key in unique:unique[key]['occurrences'].append(occurrence);continue
     uid=f'T{len(unique)+1:04d}';imgpath='textures/'+uid+'.png';im.save(OUT/imgpath)
     unique[key]={'id':uid,'image':imgpath,'width':im.width,'height':im.height,'rgba_sha256':key,'format':int(t.format),'occurrences':[occurrence],'visual_status':'unreviewed'}
  except Exception as ex:failures.append({'file':name,'error':repr(ex)})
 rows=list(unique.values())
 candidates=[]
 for r in rows:
  names=' '.join(x['file']+' '+x['texture'] for x in r['occurrences'])
  r['text_review_priority']=bool(re.search(r'box|book|label|sign|paper|poster|title|logo|menu|moji|text|news|calendar|kanban|ticket|pack|bottle|tv|shop|letter',names,re.I))
  if r['text_review_priority']:candidates.append(r)
 for label,subset in [('priority',candidates),('all',rows)]:
  for i in range(0,len(subset),30):
   items=[(r['id']+' '+r['occurrences'][0]['texture'],Image.open(OUT/r['image'])) for r in subset[i:i+30]]
   grid(items,OUT/'boards'/f'textures-{label}-{i//30:02d}.png')
 # Full-size product cards and casino rules, not shrunken whole-group sheets.
 groups=json.loads((ROOT/'metadata/translation_scope_graphics.json').read_text(encoding='utf-8'))['groups']
 for label,pred in [('products',lambda n:n.startswith('TVSp')),('casino',lambda n:n.startswith('Casino') and 'P' in n and n not in ('CasinoPorker',))]:
  selected=[r for r in groups if pred(Path(r['stem']).name)]
  for i in range(0,len(selected),12):
   items=[(r['id']+' '+Path(r['stem']).name,Image.open(ROOT/'work/scope-review'/r['cells'][0]['image'])) for r in selected[i:i+12]]
   grid(items,OUT/'boards'/f'{label}-{i//12:02d}.png',cols=4,box=(280,280))
 # Recover shared sand backgrounds using cross-resource tile-range checks.
 bg=[]
 for mapname in ['2d/SandPan.NSCR','2d/SandBGDef.NSCR']:
  for e in inv['entries']:
   if e['extension']!='.ncgr' or not e['path'].startswith('2d/Sand'):continue
   stem=e['path'][:-5]
   try:
    ts,bpp=tiles(files[e['path']]);pal=palette(files[stem+'.NCLR']);im=screen(files[mapname],ts,pal,bpp)
    output='backgrounds/'+Path(mapname).stem+'--'+Path(stem).name+'.png';im.save(OUT/output)
    bg.append({'map':mapname,'tiles':e['path'],'palette':stem+'.NCLR','image':output,'status':'tile_indices_fit_not_runtime_linked'})
   except (AssertionError,IndexError,KeyError):pass
 for i in range(0,len(bg),12):grid([(Path(r['map']).stem+'/'+Path(r['tiles']).stem,Image.open(OUT/r['image'])) for r in bg[i:i+12]],OUT/'boards'/f'backgrounds-{i//12:02d}.png',cols=4,box=(280,280))
 # Source-code filename occurrence evidence, without conflating strings with load calls.
 refs=[]
 needles=['SandPan.NSCR','SandBGDef.NSCR','SandBGBmDefS.NCGR','Aid.ntft','Aid.ntfp']
 for code in (ROOT/'work/code').glob('*.bin'):
  raw=code.read_bytes()
  for needle in needles:
   for match in re.finditer(re.escape(needle.encode()),raw):refs.append({'binary':code.name,'string':needle,'offset':match.start(),'nearby_hex':raw[max(0,match.start()-24):match.end()+24].hex()})
 report={'source_sha256':original['sha256'],'texture_palette_pairs_rendered':pair_count,'unique_rendered_textures':len(rows),'priority_texture_count':len(candidates),
         'material_pairing_failures':failures,'unbound_textures':unbound,'textures':rows,'background_candidates':bg,'code_filename_evidence':refs,
         'limits':'Texture palette pairs come from shared MDL0 material IDs. A texture preview is not the model UV layout. Background tile fit alone does not prove runtime pairing.'}
 (ROOT/'metadata/scope_followup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print({k:v for k,v in report.items() if k in ['texture_palette_pairs_rendered','unique_rendered_textures','priority_texture_count']})
 print('failures',len(failures),'unbound',len(unbound),'background candidates',len(bg),'filename refs',len(refs))
 if failures:print(failures[:3])


if __name__=='__main__':main()
