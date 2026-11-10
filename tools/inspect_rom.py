from pathlib import Path
import json,struct,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def main():
 rom=next(ROOT.glob('*.nds'));data=rom.read_bytes();fo,fs=u32(data,0x40),u32(data,0x44);ao,asz=u32(data,0x48),u32(data,0x4c);fnt=data[fo:fo+fs];fat=[struct.unpack_from('<II',data,ao+i) for i in range(0,asz,8)];entries=[];seen=set()
 def visit(did,parent):
  assert did not in seen;seen.add(did);off=(did-0xf000)*8;sub,first,_=struct.unpack_from('<IHH',fnt,off);pos=sub;fid=first
  while True:
   n=fnt[pos];pos+=1
   if not n:break
   name=fnt[pos:pos+(n&127)].decode('shift_jis');pos+=n&127;path=parent+'/'+name if parent else name
   assert '..' not in Path(path).parts and not Path(path).is_absolute()
   if n&128:
    child=struct.unpack_from('<H',fnt,pos)[0];pos+=2;visit(child,path)
   else:
    a,b=fat[fid];assert 0<=a<=b<=len(data);blob=data[a:b];entries.append({'id':fid,'path':path,'offset':a,'size':b-a,'magic_hex':blob[:16].hex(),'magic_ascii':''.join(chr(x) if 32<=x<127 else '.' for x in blob[:16]),'extension':Path(path).suffix.lower(),'sha256':hashlib.sha256(blob).hexdigest()});fid+=1
 visit(0xf000,'')
 ids={e['id'] for e in entries};report={'rom_sha256':hashlib.sha256(data).hexdigest(),'fat_count':len(fat),'named_files':len(entries),'directories':len(seen),'unnamed_file_ids':sorted(set(range(len(fat)))-ids),'extensions':dict(collections.Counter(e['extension'] for e in entries)),'entries':entries}
 (ROOT/'metadata/filesystem_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='entries'},ensure_ascii=False,indent=2))
 for e in entries:
  if any(x in e['path'].lower() for x in ['font','msg','mess','text','script']) or e['magic_ascii'].startswith(('MESG','RTFN')):print(e['id'],e['path'],e['size'],e['magic_ascii'])
 print('FIRST FILES')
 for e in entries[:45]:print(e['path'],e['size'],e['magic_ascii'])
if __name__=='__main__':main()
