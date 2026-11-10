"""저장 멈춤 가르기용 시험 롬 4(2026-11-08): 시험 롬 1(조사 패치 뺀 v11)에서 MsgResTonpy.bmg의 지정 메시지만 원본 일본어로 되돌린다.
시험 롬 3(MsgResTonpy.bmg 전부 원본)은 정상 저장됐다. 사용: python build_test_tonpy_msg.py 231 [232 ...]"""
from pathlib import Path
import sys,json,hashlib,ctypes,shutil,struct
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-test-tonpy-msg';DESKNAME='ChibiRobo_B62J_KO.nds';NAME_BMG='MsgResTonpy.bmg'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()

def sections(b):
    s={};off=0x20
    while off<len(b):
        mag=bytes(b[off:off+4]);sz=struct.unpack_from('<I',b,off+4)[0]
        if sz==0:break
        s[mag]=(off,sz);off+=sz
    return s

def messages(b):
    """메시지별 원본 바이트(끝 0 포함). 메시지는 DAT1 안에서 오프셋 순으로 붙어 있다고 보지 않고, 0 종료까지 읽는다."""
    s=sections(b);io,_=s[b'INF1'];n,esz=struct.unpack_from('<HH',b,io+8);do,dsz=s[b'DAT1']
    out=[]
    for i in range(n):
        off=struct.unpack_from('<I',b,io+16+i*esz)[0];j=do+8+off;start=j
        while True:
            c=b[j]
            if c==0x1a:j+=b[j+1];continue
            if c==0:j+=1;break
            j+=2 if (0x81<=c<0xa0 or c>=0xe0) else 1
        out.append((off,bytes(b[start:j])))
    return s,n,esz,out

def replace_messages(kb,ob,idx,custom=None):
    """idx: 원본으로 되돌릴 메시지 번호. custom: {번호: 새 바이트(끝 0 포함)}."""
    s,n,esz,km=messages(kb);_,n2,_,om=messages(ob);assert n==n2
    custom=custom or {}
    om=[(o,custom[i]) if i in custom else (o,m) for i,(o,m) in enumerate(om)];idx=set(idx)|set(custom)
    io,isz=s[b'INF1'];do,dsz=s[b'DAT1']
    # 오프셋 0(빈 메시지 공유)은 그대로 두고, 나머지는 순서대로 다시 쌓는다
    assert kb[do+8]==0
    data=bytearray(b'\0');inf=bytearray(kb[io:io+isz])
    for i,(off,m) in enumerate(km):
        if i in idx:m=om[i][1]
        if off==0 and i not in idx:continue
        if m==b'\0':struct.pack_into('<I',inf,16+i*esz,0);continue
        struct.pack_into('<I',inf,16+i*esz,len(data));data+=m
    data+=bytes((-len(data))%32)
    dat=bytearray(b'DAT1')+struct.pack('<I',len(data)+8)+data
    rest=bytes(kb[do+dsz:])
    out=bytearray(kb[:io])+inf+bytes(kb[io+isz:do])+dat+rest
    struct.pack_into('<I',out,8,len(out))
    # 확인
    _,_,_,nm=messages(bytes(out))
    for i in range(n):assert nm[i][1]==(om[i][1] if i in idx else km[i][1]),i
    return bytes(out)

def main():
    # 인자: 231 = 원본으로, fw231 = 한글 그대로 두고 반각 공백(0x20)만 전각(0x8140)으로
    # txt231=앞|뒤 = 제어 코드 앞·뒤 글을 시험 문장으로(한글은 fulltext_v07 코드표, 나머지 Shift-JIS)
    idx={int(a) for a in sys.argv[1:] if a.isdigit()};fw={int(a[2:]) for a in sys.argv[1:] if a.startswith('fw')}
    txt={int(a[3:a.index('=')]):a[a.index('=')+1:] for a in sys.argv[1:] if a.startswith('txt')};assert idx or fw or txt
    OUT.mkdir(exist_ok=True)
    original=read('metadata/originals.json')['roms'][0];source=(ROOT/original['file']).read_bytes();assert sha(source)==original['sha256']
    v11=NintendoDSRom((ROOT/'work/output-graphics-v11/ChibiRobo_B62J_KO_graphics_v11.nds').read_bytes());orig=NintendoDSRom(source)
    replacements={}
    for i,data in enumerate(v11.files):
        n=v11.filenames.filenameOf(i) or ''
        if data!=orig.files[i]:replacements[n]=bytes(data)
    fid=orig.filenames.idOf(NAME_BMG)
    _,_,_,km=messages(replacements[NAME_BMG])
    custom={}
    for i in fw:
        m=km[i][1];out=bytearray();j=0
        while j<len(m):
            c=m[j]
            if c==0x1a:out+=m[j:j+m[j+1]];j+=m[j+1];continue
            if c==0x20:out+=bytes([0x81,0x40]);j+=1;continue
            w=2 if (0x81<=c<0xa0 or c>=0xe0) else 1;out+=m[j:j+w];j+=w
        assert out!=m,('no half-width space',i);custom[i]=bytes(out)
    if txt:
        codes={x['character']:int(x['code_hex'],16) for x in read('metadata/fulltext_build_v07.json')['mapping']}
        def enc(t):
            b=bytearray()
            for ch in t:
                if ch in codes:c=codes[ch];b+=bytes([c>>8,c&255])
                else:b+=ch.encode('shift_jis')
            return bytes(b)
        for i,t in txt.items():
            m=km[i][1];k=m.index(0x1a);tag=m[k:k+m[k+1]];a,b=t.split('|')
            custom[i]=enc(a)+tag+enc(b)+bytes(1)
    replacements[NAME_BMG]=replace_messages(replacements[NAME_BMG],bytes(orig.files[fid]),idx,custom)
    result,records=build(source,replacements)
    r=NintendoDSRom(result);assert r.arm9==orig.arm9
    name=f"ChibiRobo_B62J_KO_v11_tonpy_{'_'.join([str(i) for i in sorted(idx)]+['fw'+str(i) for i in sorted(fw)]+['txt'+str(i) for i in sorted(txt)])}.nds";(OUT/name).write_bytes(result)
    buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/DESKNAME
    shutil.copy2(OUT/name,desktop);assert sha(desktop.read_bytes())==sha(result)
    print(json.dumps(dict(output=str((OUT/name).relative_to(ROOT)),original_messages=sorted(idx),fullwidth_space_messages=sorted(fw),test_text={str(k):v for k,v in txt.items()},sha256=sha(result),desktop=str(desktop)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
