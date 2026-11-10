"""Patch only approved texture pixel bytes; leave models, UVs and palettes intact."""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from PIL import Image
import ndspy.color,ndspy.texture
from survey_scope_deep import info,U16,U32
from build_graphics_2d import rgba_equal
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'work/output-graphics-v01/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def parse(b):
 off=next(v for v in struct.unpack_from('<'+'I'*U16(b,14),b,16) if b[v:v+4]==b'TEX0');tx=b[off:off+U32(b,off+4)];d=ndspy.texture._readTEX0(tx)
 paloff,palbase=struct.unpack_from('<II',tx,0x34);pallen=U16(tx,0x30)*8;pd={n:U16(v,0)*8 for n,v in info(tx,paloff,4)};offsets=sorted(set(pd.values())|{pallen});ps={}
 for name,start in pd.items():
  end=next(x for x in offsets if x>start);ps[name]=list(struct.unpack('<'+'H'*((end-start)//2),tx[palbase+start:palbase+end]))
 texoff=U16(tx,0xE);base=U32(tx,0x14);locations={n:off+base+U16(v,0)*8 for n,v in info(tx,texoff,8)}
 return dict(d['textures']),ps,locations

def unpack(data,fmt):
 a=np.frombuffer(data,np.uint8)
 if fmt==2:return np.stack([a>>shift&3 for shift in (0,2,4,6)],1).reshape(-1)
 if fmt==3:return np.stack([a&15,a>>4],1).reshape(-1)
 assert fmt in (1,4,6);return a.copy()

def pack(codes,fmt):
 if fmt==2:return np.sum(codes.reshape(-1,4).astype(np.uint8)<<np.array([0,2,4,6],np.uint8),1).astype(np.uint8).tobytes()
 if fmt==3:return (codes[::2]|codes[1::2]<<4).astype(np.uint8).tobytes()
 return codes.astype(np.uint8).tobytes()

def render(t,data,pal):return np.array(ndspy.texture.renderTextureDataAsImage(data,t.data2,t.format,t.width,t.height,pal,t.isColor0Transparent).convert('RGBA'))
def main():
 ndspy.color.prepareLUTs();original=read('metadata/originals.json')['roms'][0];rom=(ROOT/original['file']).read_bytes();inv={r['path']:r for r in read('metadata/filesystem_inventory.json')['entries']};files={};out={};edited={};reports=[]
 for row in read('metadata/graphics_worklist.json')['items']:
  if row['kind']!='3D':continue
  for a in row['assets']:
   if a.get('draft_stage')!='approved':continue
   png=np.array(Image.open(ROOT/'work/graphics-review'/a['result_image']).convert('RGBA'))
   for occ in a['occurrences']:
    name=occ['file'];e=inv[name]
    if name not in files:files[name]=rom[e['offset']:e['offset']+e['size']];out[name]=bytearray(files[name]);edited[name]=set()
    ts,ps,locs=parse(files[name]);t=ts[occ['texture']];pal=ps[occ['palette']];fmt=int(t.format);assert fmt in (1,2,3,4,6)
    n={1:256,2:4,3:16,4:256,6:256}[fmt];codes=np.arange(n,dtype=np.uint8);lut=np.array(ndspy.texture.renderTextureDataAsImage(pack(codes,fmt),b'',fmt,n,1,pal,t.isColor0Transparent).convert('RGBA'))[0]
    old=render(t,t.data1,pal);assert old.shape==png.shape
    unique,rev=np.unique(png.reshape(-1,4),axis=0,return_inverse=True);dist=((unique[:,None,:].astype(np.int32)-lut[None].astype(np.int32))**2).sum(2);m=dist.argmin(1).astype(np.uint8);new=m[rev]
    previous=unpack(t.data1,fmt);eq=rgba_equal(old,png).reshape(-1);new[eq]=previous[eq];data=pack(new,fmt);assert len(data)==len(t.data1)
    result=render(t,data,pal);assert rgba_equal(result,png).all(),(row['id'],int((~rgba_equal(result,png)).sum()))
    start=locs[occ['texture']];assert files[name][start:start+len(data)]==t.data1
    out[name][start:start+len(data)]=data;edited[name].add(occ['texture'])
    reports.append(dict(asset=row['id'],file=name,texture=occ['texture'],palette=occ['palette'],format=fmt,offset=start,length=len(data),changed_bytes=sum(x!=y for x,y in zip(data,t.data1)),decoded_readback_exact=True))
 replacements=[]
 for name,b in out.items():
  old=files[name];allowed=np.zeros(len(b),bool)
  for rr in reports:
   if rr['file']==name:allowed[rr['offset']:rr['offset']+rr['length']]=True
  assert len(old)==len(b);assert not (np.frombuffer(old,np.uint8)[~allowed]!=np.frombuffer(b,np.uint8)[~allowed]).any()
  ts,ps,loc=parse(old);nts,nps,nloc=parse(bytes(b));assert ps==nps and loc==nloc
  for tn,t in ts.items():
   if tn not in edited[name]:assert t.data1==nts[tn].data1 and t.data2==nts[tn].data2,(name,tn)
  p=RES/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);replacements.append(dict(file=name,size=len(b),sha256=hashlib.sha256(b).hexdigest()))
 report=dict(approved_assets=len({r['asset'] for r in reports}),texture_occurrences=len(reports),files=len(out),textures=reports,replacements=replacements,model_uv_palette_bytes_unchanged=True,unapproved_textures_unchanged=True,rom_modified=False)
 (ROOT/'metadata/graphics_3d_build_v01.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('3D:',report['approved_assets'],'assets,',len(reports),'occurrences,',len(out),'files, exact readback')
if __name__=='__main__':main()
