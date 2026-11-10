from pathlib import Path
import struct,json,hashlib
import numpy as np
from PIL import Image,ImageFont,ImageDraw
from ndspy.bmg import BMG
from analyze_text_fonts import blocks,u16,u32
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/hangul-probe-prep';FONTDIR=Path.home()/'AppData/Local/Microsoft/Windows/Fonts'
SPECS={'Font_large.NFTR':('Galmuri14',16),'Font_normal.NFTR':('Galmuri11',12),'Font_small.NFTR':('Galmuri9',10),'Font_smallsmall.NFTR':('Galmuri7',8)}
TEXTS=[('MsgResFamily.bmg',2,'이제야 왔구나?'),('MsgResFamily.bmg',3,'꼬마야\n한참 기다렸어!'),('MsgResSys.bmg',722,'데이터를 복사했습니다')]
def align(b):return b+b'\0'*((-len(b))%4)
def parsefont(b):
 bs=blocks(b,u16(b,12));mp={};ci=next(o for k,o,n in bs if k=='PLGC');wi=next(o for k,o,n in bs if k=='HDWC');count=u16(b,wi+10)+1;cell=u16(b,ci+10)
 for k,o,n in bs:
  if k!='PAMC':continue
  first,last,method=struct.unpack_from('<HHH',b,o+8)
  if method==0:
   base=u16(b,o+20);mp.update((c,base+c-first) for c in range(first,last+1))
  elif method==1:mp.update((c,u16(b,o+20+2*(c-first))) for c in range(first,last+1) if u16(b,o+20+2*(c-first))!=65535)
  elif method==2:mp.update(struct.unpack_from('<HH',b,o+22+4*i) for i in range(u16(b,o+20)))
 return bs,mp,ci,wi,count,cell

def expand(b,codes,spec):
 bs,mp,ci,wi,count,cell=parsefont(b);w,h=b[ci+8:ci+10];assert b[ci+14]==1 and u16(b,wi+8)==0;assert sum(k=='HDWC' for k,o,n in bs)==1
 font=ImageFont.truetype(str(FONTDIR/(spec[0]+'.ttf')),spec[1]);newglyphs=[];previews={}
 for char in codes:
  tmp=Image.new('1',(40,40));d=ImageDraw.Draw(tmp);d.fontmode='1';d.text((4,4),char,font=font,fill=1);box=tmp.getbbox();g=tmp.crop(box);gw,gh=g.size;assert gw<=w and gh<=h,(char,spec,box,w,h)
  im=Image.new('1',(w,h));im.paste(g,((w-gw)//2,h-gh))
  raw=np.packbits(np.array(im,dtype=np.uint8).reshape(-1)).tobytes();assert len(raw)<=cell;newglyphs.append(raw.ljust(cell,b'\0'));previews[char]=im.convert('L').point(lambda v:255-v)
 chunks=[]
 full_maps=[o for k,o,n in bs if k=='PAMC' and u16(b,o+8)==0 and u16(b,o+10)==65535 and u16(b,o+12)==2]
 assert len(full_maps)==1, 'Expected one full-range sparse mapping'
 full_map=full_maps[0]
 for k,o,n in bs:
  q=bytearray(b[o:o+n])
  if k=='PLGC':q=bytearray(align(bytes(q[:16+count*cell])+b''.join(newglyphs)))
  if k=='HDWC':
   q=bytearray(align(bytes(q[:16+count*3])+bytes([0,w,w])*len(codes)));struct.pack_into('<H',q,10,count+len(codes)-1)
  if o==full_map:
   pairs=dict(struct.unpack_from('<HH',b,o+22+4*i) for i in range(u16(b,o+20)))
   assert not (set(codes.values()) & set(mp)), 'New character codes must be unused'
   pairs.update((code,count+i) for i,code in enumerate(codes.values()))
   q=bytearray(align(bytes(q[:20])+struct.pack('<H',len(pairs))+b''.join(struct.pack('<HH',c,g) for c,g in sorted(pairs.items()))))
  struct.pack_into('<I',q,4,len(q));chunks.append((k,o,q))
 offsets={};pos=16
 for k,o,q in chunks:offsets[o]=pos;pos+=len(q)
 for k,o,q in chunks:
  if k=='FNIF':
   for off in (16,20,24):struct.pack_into('<I',q,off,offsets[u32(q,off)-8]+8)
  if k=='HDWC' and u32(q,12):struct.pack_into('<I',q,12,offsets[u32(q,12)-8]+8)
  if k=='PAMC':
   nxt=u32(q,16);struct.pack_into('<I',q,16,offsets[nxt-8]+8 if nxt else 0)
 header=bytearray(b[:16]);struct.pack_into('<I',header,8,pos);struct.pack_into('<H',header,14,len(chunks));result=bytes(header)+b''.join(bytes(q) for _,_,q in chunks)
 nbs,nmp,nci,nwi,ncount,ncell=parsefont(result);assert ncount==count+len(codes);assert all(nmp[c]==g for c,g in mp.items());assert result[nci+16:nci+16+count*cell]==b[ci+16:ci+16+count*cell];assert result[nwi+16:nwi+16+count*3]==b[wi+16:wi+16+count*3]
 for i,(ch,code) in enumerate(codes.items()):assert nmp[code]==count+i
 return result,previews,{'cell':[w,h],'old_glyphs':count,'new_glyphs':ncount,'added_glyphs':len(codes),'old_glyph_bytes_preserved':True,'old_width_entries_preserved':True,'old_code_mappings_preserved':True,'old_size':len(b),'new_size':len(result),'font_family':spec[0],'font_px':spec[1]}

def main():
 OUT.mkdir(exist_ok=True);src=ROOT/'work/extracted';chars=list(dict.fromkeys(c for _,_,t in TEXTS for c in t if ord(c)>=0xac00 and ord(c)<=0xd7a3));used=set()
 for name in SPECS:used.update(parsefont((src/name).read_bytes())[1])
 available=[]
 for code in range(0x889f,0x9873):
  if code in used:continue
  try:code.to_bytes(2,'big').decode('shift_jis')
  except UnicodeDecodeError:continue
  available.append(code)
 codes=dict(zip(chars,available));assert len(codes)==len(chars);fontchecks=[];previewfonts={}
 for name,spec in SPECS.items():
  b=(src/name).read_bytes();updated,imgs,rec=expand(b,codes,spec);(OUT/name).write_bytes(updated);rec.update({'file':name,'sha256':hashlib.sha256(updated).hexdigest(),'runtime_verified':False});fontchecks.append(rec);previewfonts[name]=imgs
 # Read the actual rebuilt glyph bytes back for visual previews.
 for name,imgs in previewfonts.items():
  b=(OUT/name).read_bytes();_,mp,ci,wi,count,cell=parsefont(b);w,h=b[ci+8:ci+10]
  for ch,code in codes.items():
   raw=b[ci+16+mp[code]*cell:ci+16+(mp[code]+1)*cell];pix=np.unpackbits(np.frombuffer(raw,dtype=np.uint8))[:w*h].reshape(h,w);im=Image.fromarray((255-pix*255).astype('uint8'));assert np.array_equal(np.array(imgs[ch]),np.array(im));imgs[ch]=im
 textchecks=[]
 for name in sorted({n for n,_,_ in TEXTS}):
  obj=BMG((src/name).read_bytes());before=[m.save(obj.encoding) for m in obj.messages];changes={idx:t for n,idx,t in TEXTS if n==name}
  for idx,t in changes.items():
   assert all(isinstance(p,str) for p in obj.messages[idx].stringParts);proxy=''.join(codes[c].to_bytes(2,'big').decode('shift_jis') if c in codes else c for c in t);obj.messages[idx].stringParts=[proxy]
  raw=obj.save();(OUT/name).write_bytes(raw);again=BMG(raw);after=[m.save(again.encoding) for m in again.messages];assert all(a==b for i,(a,b) in enumerate(zip(before,after)) if i not in changes)
  for idx,t in changes.items():
   expected=b''.join(codes[c].to_bytes(2,'big') if c in codes else c.encode('shift_jis') for c in t)+b'\0';assert after[idx]==expected;textchecks.append({'file':name,'index':idx,'korean':t,'encoded_hex':expected.hex(),'old_bytes':len(before[idx]),'new_bytes':len(after[idx]),'other_messages_unchanged':True,'runtime_entrypoint_verified':False})
 report={'method':'Append new glyphs and valid unused Shift-JIS code mappings; original glyphs retained','mapping':[{'hangul':ch,'code_hex':f'{code:04X}','new_glyph_id':1015+i} for i,(ch,code) in enumerate(codes.items())],'fonts':fontchecks,'messages':textchecks,'loadinfo_modified':False,'rom_built':False,'hangul_runtime_verified':False,'purpose':'Offline font and message preparation only, not approved final translation'}
 (ROOT/'metadata/hangul_probe_preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 sheet=Image.new('RGB',(900,len(SPECS)*135),'#e9ebdf');draw=ImageDraw.Draw(sheet)
 for i,(name,imgs) in enumerate(previewfonts.items()):
  draw.text((10,i*135+5),name,fill='black');x=10;y=i*135+30
  for c in chars:
   im=imgs[c].resize((imgs[c].width*2,imgs[c].height*2),Image.Resampling.NEAREST)
   if x+im.width>885:x=10;y+=40
   sheet.paste(im,(x,y));x+=im.width+7
 sheet.save(OUT/'glyphs-preview.png')
 print('Prepared',len(chars),'new glyphs per font; messages',len(textchecks))
 for r in fontchecks:print(r['file'],r['old_glyphs'],'->',r['new_glyphs'],r['old_size'],'->',r['new_size'])
 print('Mapping',report['mapping'])
if __name__=='__main__':main()
