"""조사 패치 모의 실행 검사: 패치된 ARM9를 유니콘에 올리고, 래퍼(=실제 서식 함수 + 조사 루틴)를 직접 불러 결과를 읽는다.
malloc(0x0212A854)·free(0x0212A848)만 가짜로 대신한다(힙 초기화 없이 돌리기 위해). 나머지는 게임 코드 그대로."""
import sys,json,struct
from pathlib import Path
from ndspy.rom import NintendoDSRom
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
import particle_b62j as PB
ROOT=Path(__file__).resolve().parents[1]
MALLOC,FREE=0x0212A854,0x0212A848
STOP=0x02FF0000
def run(rom_path,meta_path,cases):
    rom=NintendoDSRom.fromFile(str(rom_path));m=rom.loadArm9()
    meta=json.load(open(meta_path,encoding='utf-8'))
    codes={x['character']:int(x['code_hex'],16) for x in meta['mapping']};m0=int(meta['particles']['marker0'],16)
    rev={v:k for k,v in codes.items()}
    def enc(s):
        s=PB.to_placeholders(s);b=bytearray()
        for ch in s:
            o=ord(ch)-PB.PLACEHOLDER
            if 0<=o<8:c=m0+o
            elif ch in codes:c=codes[ch]
            else:
                e=ch.encode('shift_jis');b+=e;continue
            b+=bytes([c>>8,c&0xff])
        return bytes(b)+b'\0'
    def dec(b):
        out=[];i=0
        while i<len(b) and b[i]:
            x=b[i]
            if 0x81<=x<0xa0 or x>=0xe0:
                c=(x<<8)|b[i+1];i+=2
                if c in rev:out.append(rev[c])
                elif 0x8740<=c<=0x8749:out.append('1234567890'[c-0x8740])
                elif m0<=c<m0+8:out.append('[표시%d]'%(c-m0))
                else:out.append(bytes([c>>8,c&0xff]).decode('shift_jis','replace'))
            elif x==0x1a:
                n=b[i+1];out.append('<tag>');i+=max(n,2)
            else:out.append(chr(x));i+=1
        return ''.join(out)
    mu=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    mu.mem_map(0x01FF8000,0x8000);mu.mem_map(0x02000000,0x400000);mu.mem_map(0x027E0000,0x4000);mu.mem_map(0x02FF0000,0x1000);mu.mem_map(0x03000000,0x100000)
    for s in m.sections:mu.mem_write(s.ramAddress,bytes(s.data))
    heap=[0x03000000]
    def hook(uc,addr,size,_):
        if addr in (MALLOC,FREE,MALLOC|1,FREE|1):
            if addr&~1==MALLOC:
                n=uc.reg_read(UC_ARM_REG_R0);p=heap[0];heap[0]+=(n+15)&~15;uc.mem_write(p,bytes(n));uc.reg_write(UC_ARM_REG_R0,p)
            lr=uc.reg_read(UC_ARM_REG_LR);cpsr=uc.reg_read(UC_ARM_REG_CPSR)
            uc.reg_write(UC_ARM_REG_CPSR,(cpsr&~0x20)|(0x20 if lr&1 else 0));uc.reg_write(UC_ARM_REG_PC,lr&~1)
    mu.hook_add(UC_HOOK_CODE,hook,begin=MALLOC&~1,end=MALLOC+2);mu.hook_add(UC_HOOK_CODE,hook,begin=FREE&~1,end=FREE+2)
    res=[]
    for fmt,args,expect in cases:
        heap[0]=0x03000000;FMT=0x03080000;BUF=0x03090000;VA=0x030A0000;ARGS=0x030B0000
        mu.mem_write(FMT,enc(fmt));mu.mem_write(BUF,bytes(0x400))
        vals=[];p=ARGS
        for a in args:
            if isinstance(a,int):vals.append(a)
            else:mu.mem_write(p,enc(a));vals.append(p);p+=0x100
        mu.mem_write(VA,b''.join(struct.pack('<I',v) for v in vals))
        mu.reg_write(UC_ARM_REG_CPSR,0x1f)
        mu.reg_write(UC_ARM_REG_SP,0x027E3F00);mu.reg_write(UC_ARM_REG_LR,STOP)
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(3,BUF,FMT,VA)):mu.reg_write(r,v)
        mu.emu_start(PB.ITCM_BASE,STOP,count=2_000_000)
        got=dec(bytes(mu.mem_read(BUF,0x400)));res.append((fmt,args,got,expect,got.replace('<tag>','')==expect))  # 숫자 앞뒤 태그는 게임이 원래 넣는 것
    return res
if __name__=='__main__':
    rom_path,meta_path=sys.argv[1],sys.argv[2]
    names=['치비 청소기','치비 체','물','하바네로','먼지','스티커','집','레벨','달','반짝반짝 별']
    cases=[]
    for n in names:
        last=n[-1]
        cls=PB.batchim_class(last)
        def pick(a,b,eu=False):return a if (cls>=2 if eu else cls>=1) else b
        cases.append(('%s을(를) 건네드려요!',[n],f"{n}{pick('을','를')} 건네드려요!"))
        cases.append(('%s이(가)/입고됐어요!',[n],f"{n}{pick('이','가')}/입고됐어요!"))
        cases.append(('『%s』(으)로 레벨 업!',[n],f"『{n}』{pick('으','',True)}로 레벨 업!"))
        cases.append(('『%s』(이)에요!',[n],f"『{n}』{pick('이에','예')}요!"))
        cases.append(('%s은(는) 어때?',[n],f"{n}{pick('은','는')} 어때?"))
    for v,ex in ((1,'일'),(2,'이'),(3,'삼'),(10,'영')):
        c=PB.DIGIT_CLASS['0123456789'.index(str(v)[-1])]
        cases.append(('%d개이(가) 남았다',[v],f"{v}개{'이' if PB.batchim_class('개')>=1 else '가'} 남았다"))
        cases.append(('%d을(를) 골랐다',[v],f"{v}{'을' if c>=1 else '를'} 골랐다"))
    res=run(rom_path,meta_path,cases)
    ok=sum(r[4] for r in res);print('맞음',ok,'/',len(res))
    for r in res:
        if not r[4]:print('틀림',r)
    for r in res[:6]:print(r[2])
