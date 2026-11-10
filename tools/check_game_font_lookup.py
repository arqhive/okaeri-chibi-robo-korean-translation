"""Run the ROM's actual Thumb font unpack/lookup code in Unicorn, not the game."""
from pathlib import Path
import json
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
from prepare_hangul_probe import ROOT, parsefont

FONT = 0x02300000
CONTEXT = 0x02380000
STOP = 0x023FF000


class GameFontLookup:
    def __init__(self, raw):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.uc.mem_map(0x02000000, 0x400000)
        self.uc.mem_write(0x02000000, (ROOT/'work/code/arm9.bin').read_bytes())
        self.uc.mem_write(FONT, raw)
        self.call(0x0210FAD0, FONT, 0)
        blocks, *_ = parsefont(raw)
        finf = next(off for kind, off, size in blocks if kind=='FNIF')
        self.uc.mem_write(CONTEXT, struct.pack('<I',FONT+finf+8))

    def call(self, address, r0, r1):
        self.uc.reg_write(UC_ARM_REG_SP,0x023F0000)
        self.uc.reg_write(UC_ARM_REG_LR,STOP|1)
        self.uc.reg_write(UC_ARM_REG_R0,r0)
        self.uc.reg_write(UC_ARM_REG_R1,r1)
        self.uc.emu_start(address|1,STOP,count=200000)
        assert self.uc.reg_read(UC_ARM_REG_PC)==STOP, 'Font routine did not return'
        return self.uc.reg_read(UC_ARM_REG_R0)

    def lookup(self,code):
        return self.call(0x0210EE2C,CONTEXT,code)

    def widths(self,glyph):
        ptr=self.call(0x0210EE58,CONTEXT,glyph)
        return bytes(self.uc.mem_read(ptr,3))


def check_v02():
    report=json.loads((ROOT/'metadata/probe_build_v02.json').read_text(encoding='utf-8'))
    results=[]
    for font in report['fonts']:
        name=font['file'];game=GameFontLookup((ROOT/'work/output-probe/v02-resources'/name).read_bytes())
        checks=[{'character':m['hangul'],'code':m['code_hex'],'expected':m['glyph_id'],
                 'actual':game.lookup(int(m['code_hex'],16))} for m in report['mapping']]
        results.append({'file':name,'hangul_total':len(checks),'failed':sum(x['actual']!=x['expected'] for x in checks),'checks':checks})
    out={'method':'Unicorn executes original Thumb unpack 0x0210FAD0, lookup 0x0210EE2C and its subroutine from local ARM9',
         'full_game_emulation':False,'finding':'Lookup returns after first CMAP range match. Existing full-range CMAP shadows appended Hangul CMAP.', 'fonts':results}
    (ROOT/'metadata/v02_lookup_regression.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in results:print(r['file'],r['failed'],'/',r['hangul_total'],'new glyph lookups failed')


if __name__=='__main__':check_v02()
