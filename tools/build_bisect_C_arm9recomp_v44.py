"""대조판 C(2026-11-11): 대조판 B(ARM9 원본·오버레이 코드 문자열) + ARM9만 「원본 그대로 ndspy로 다시 압축」.
문자열은 하나도 안 바꿈. 실기 결과: B 정상, v44(ARM9 문자열 바꿔 다시 압축) 오류 → C로 「다시 압축」 자체가 원인인지 가른다."""
from pathlib import Path
import json, hashlib, ctypes, shutil, struct
import ndspy._common
from ndspy.rom import NintendoDSRom
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'work/output-bisect/ChibiRobo_B62J_KO_test_B_ovonly_v44.nds'
OUT = ROOT / 'work/output-bisect/ChibiRobo_B62J_KO_test_C_arm9recomp_v44.nds'
def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def main():
    o = json.loads((ROOT / 'metadata/originals.json').read_text('utf8'))['roms'][0]
    src = (ROOT / o['file']).read_bytes(); assert hashlib.sha256(src).hexdigest() == o['sha256']
    b = bytearray(B.read_bytes()); rb = NintendoDSRom(bytes(b))
    so = NintendoDSRom(src); assert rb.arm9 == so.arm9, 'B의 ARM9은 원본이어야 함'
    m = so.loadArm9(); arm9 = m.save(compress=True); post = so.arm9PostData
    off, size = u32(b, 0x20), u32(b, 0x2C)
    assert b[off + size: off + size + len(post)] == post
    end = off + len(arm9) + len(post); assert end <= u32(b, 0x50), (hex(end), hex(u32(b, 0x50)))
    b[off:u32(b, 0x50)] = b'\xFF' * (u32(b, 0x50) - off)
    b[off:off + len(arm9)] = arm9; b[off + len(arm9):end] = post
    struct.pack_into('<I', b, 0x2C, len(arm9))
    struct.pack_into('<H', b, 0x15E, ndspy._common.crc16(bytes(b[:0x15E])))
    r = NintendoDSRom(bytes(b)); m2 = r.loadArm9()
    for x, y in zip(m.sections, m2.sections): assert x.ramAddress == y.ramAddress and bytes(x.data) == bytes(y.data)
    assert r.files == rb.files and r.arm9OverlayTable == rb.arm9OverlayTable
    diff = [i for i in range(len(b)) if b[i] != B.read_bytes()[i]] if False else None
    OUT.write_bytes(bytes(b))
    buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
    desk = Path(buf.value) / 'ChibiRobo_B62J_KO.nds'; shutil.copy2(OUT, desk)
    md5 = hashlib.md5(bytes(b)).hexdigest(); assert hashlib.md5(desk.read_bytes()).hexdigest() == md5
    rec = dict(version='test_C_arm9recomp_v44', base='test_B_ovonly_v44', arm9_recompressed_unchanged=True,
               arm9_size_original=hex(len(so.arm9)), arm9_size_new=hex(len(arm9)), arm9_bytes_same_as_original=arm9 == so.arm9,
               header_0x80=hex(u32(b, 0x80)), md5=md5, sha256=hashlib.sha256(bytes(b)).hexdigest(), desktop=str(desk), runtime_verified=False)
    (ROOT / 'metadata/test_C_arm9recomp_v44_build.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps(rec, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()
