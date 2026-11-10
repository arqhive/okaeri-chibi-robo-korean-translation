"""대조판(2026-11-11): 조사 패치만 넣은 판(K3, 0x80 원본)이 하우스 밖 오류. 조사 패치는 (1) ITCM 아레나 앞 348바이트 사용 (2) ARM9가 커져 오버레이 표(헤더 0x50)를 롬 끝으로 옮김.
- K5_ovt_moved: 원본에서 ARM9 오버레이 표만 롬 끝(원본 데이터 끝 뒤)으로 옮김. 0x80은 원본. 이게 오류면 (2)가 원인."""
from pathlib import Path
import json, hashlib, ctypes, shutil, struct
import ndspy._common
from ndspy.rom import NintendoDSRom
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
o = json.loads((ROOT / 'metadata/originals.json').read_text('utf8'))['roms'][0]; src = (ROOT / o['file']).read_bytes()
out = bytearray(src)
off, size = struct.unpack_from('<II', out, 0x50); end = struct.unpack_from('<I', out, 0x80)[0]
fat = struct.unpack_from('<I', out, 0x48)[0]; n = struct.unpack_from('<I', out, 0x4C)[0] // 8
last = max(struct.unpack_from('<II', out, fat + 8 * i)[1] for i in range(n))
new = (max(end, last) + 511) & ~511
assert all(v == 0xFF for v in out[new:new + size])
out[new:new + size] = out[off:off + size]; out[off:off + size] = b'\xff' * size
struct.pack_into('<I', out, 0x50, new); struct.pack_into('<H', out, 0x15E, ndspy._common.crc16(bytes(out[:0x15E])))
print('오버레이 표', hex(off), '→', hex(new), '크기', size, '0x80', hex(struct.unpack_from('<I', out, 0x80)[0]))
a, b = NintendoDSRom(src), NintendoDSRom(bytes(out))
assert all(x == y for x, y in zip(a.files, b.files)) and a.arm9 == b.arm9
assert [ (k, v.ramAddress, bytes(v.data)) for k, v in a.loadArm9Overlays().items()] == [(k, v.ramAddress, bytes(v.data)) for k, v in b.loadArm9Overlays().items()]
p = OUT / 'ChibiRobo_B62J_KO_test_K5_ovt_moved.nds'; p.write_bytes(bytes(out))
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
shutil.copy2(p, Path(buf.value) / p.name); print('MD5', hashlib.md5(bytes(out)).hexdigest())
