from pathlib import Path
import json,struct,hashlib,re,collections
from ndspy import codeCompression,bmg
ROOT=Path(__file__).resolve().parents[1]
def u32(b,p):return struct.unpack_from('<I',b,p)[0]
def main():
 rompath=next(ROOT.glob('*.nds'));rom=rompath.read_bytes();inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text(encoding='utf-8'));codeout=ROOT/'work/code';codeout.mkdir(exist_ok=True);a,size=u32(rom,0x20),u32(rom,0x2c);arm=codeCompression.decompress(rom[a:a+size]);(codeout/'arm9.bin').write_bytes(arm);fat=[struct.unpack_from('<II',rom,u32(rom,0x48)+i) for i in range(0,u32(rom,0x4c),8)];oa,os=u32(rom,0x50),u32(rom,0x54);overlays=[];refs=[]
 blobs=[('arm9',arm,u32(rom,0x28))]
 for o in range(oa,oa+os,32):
  idx,ram,rs,bss,si,se,fid,flags=struct.unpack_from('<8I',rom,o);fa,fb=fat[fid];raw=rom[fa:fb];decomp=codeCompression.decompress(raw) if flags&0x1000000 else raw
  assert len(decomp)==rs,(idx,len(decomp),rs)
  (codeout/f'overlay-{idx:03}.bin').write_bytes(decomp);blobs.append((f'overlay-{idx}',decomp,ram));overlays.append({'id':idx,'file_id':fid,'compressed':bool(flags&0x1000000),'stored_bytes':len(raw),'decompressed_bytes':len(decomp),'ram_address':ram})
 targets=[e['path'] for e in inv['entries'] if e['extension'] in ['.bmg','.nftr']]
 for name,data,ram in blobs:
  for target in targets:
   for needle in [target.encode('ascii')]:
    start=0
    while (pos:=data.find(needle,start))>=0:
     refs.append({'code_blob':name,'resource':target,'matched':needle.decode(),'file_offset':pos,'ram_address':ram+pos});start=pos+len(needle)
 report={'arm9':{'stored_bytes':size,'decompressed_bytes':len(arm),'compressed':arm!=rom[a:a+size]},'overlays':overlays,'unnamed_fat_ids_match_overlay_files':set(inv['unnamed_file_ids'])=={v['file_id'] for v in overlays},'resource_string_occurrences':refs,'resource_occurrences_are_runtime_proof':False}
 (ROOT/'metadata/code_resources.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 entries=json.loads((ROOT/'metadata/text_entries.json').read_text(encoding='utf-8'));repack=[]
 for p in sorted((ROOT/'work/extracted').glob('*.bmg')):
  original=p.read_bytes();parsed=bmg.BMG(original);known=[r for r in entries if r['file']==p.name];assert len(parsed.messages)==len(known)
  raw=parsed.save();again=bmg.BMG(raw)
  assert len(again.messages)==len(parsed.messages)
  same=[x.save(parsed.encoding)==y.save(again.encoding) for x,y in zip(parsed.messages,again.messages)];assert all(same)
  repack.append({'file':p.name,'ndspy_encoding':parsed.encoding,'entries':len(parsed.messages),'no_change_file_identical':raw==original,'all_message_bytes_identical_after_serialization':all(same)})
 p=ROOT/'work/extracted/MsgResSys.bmg';parsed=bmg.BMG(p.read_bytes());before=[x.save(parsed.encoding) for x in parsed.messages];parsed.messages[20].stringParts.append(' ');raw=parsed.save();again=bmg.BMG(raw);after=[x.save(again.encoding) for x in again.messages];assert after[20]==before[20][:-1]+b' \0';assert all(x==y for i,(x,y) in enumerate(zip(before,after)) if i!=20)
 out=ROOT/'work/static-repack';out.mkdir(exist_ok=True);(out/'MsgResSys-one-space.bmg').write_bytes(raw)
 (ROOT/'metadata/bmg_repack_checks.json').write_text(json.dumps({'no_change':repack,'one_byte_length_change':{'file':'MsgResSys.bmg','entry':20,'edit':'Append one ASCII space for offline serialization test','roundtrip_readback_passed':True,'other_messages_unchanged':True,'output':'work/static-repack/MsgResSys-one-space.bmg','rom_built':False,'runtime_verified':False}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 assert hashlib.sha256(rompath.read_bytes()).hexdigest()==inv['rom_sha256']
 print('ARM9',report['arm9'],'OVERLAYS',len(overlays),'COMPRESSED',sum(x['compressed'] for x in overlays),'RESOURCE STRINGS',len(refs));print('BMG byte identical',sum(x['no_change_file_identical'] for x in repack),'/',len(repack));print('Length change offline passed')
 for r in refs[:25]:print(r['code_blob'],r['resource'],hex(r['ram_address']))
if __name__=='__main__':main()
