"""대조판 6단계(2026-11-11): 실패한 판은 모두 글꼴이 커져 롬 끝(원본 데이터 끝 0x3081CDC 뒤)으로 옮겨졌다.
크기 탓인지 위치 탓인지 가른다.
- R1_moved_fonts_keep80: 원본 글꼴 4개를 크기 그대로 롬 끝으로만 옮김(내용·크기 원본). 이게 오류면 「위치」, 아니면 「크기」."""
from pathlib import Path
import json, hashlib, ctypes, shutil, struct
import ndspy._common
from ndspy.rom import NintendoDSRom
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
o = json.loads((ROOT / 'metadata/originals.json').read_text('utf8'))['roms'][0]; src = (ROOT / o['file']).read_bytes()
rom = NintendoDSRom(src); out = bytearray(src)
fat = struct.unpack_from('<I', out, 0x48)[0]; n = struct.unpack_from('<I', out, 0x4C)[0] // 8
ranges = [struct.unpack_from('<II', out, fat + 8 * i) for i in range(n)]
cursor = (max(struct.unpack_from('<I', out, 0x80)[0], max(e for s, e in ranges)) + 511) & ~511
for name in ('Font_large.NFTR', 'Font_normal.NFTR', 'Font_small.NFTR', 'Font_smallsmall.NFTR'):
    fid = rom.filenames.idOf(name); s, e = ranges[fid]; data = bytes(out[s:e])
    assert all(v == 0xFF for v in out[cursor:cursor + len(data)])
    out[cursor:cursor + len(data)] = data; out[s:e] = b'\xff' * (e - s)       # 원래 자리는 비움
    struct.pack_into('<II', out, fat + 8 * fid, cursor, cursor + len(data)); print(name, hex(s), '→', hex(cursor))
    end = cursor + len(data); cursor = (end + 511) & ~511
# R1: 헤더 0x80(사용 크기)은 원본 값 그대로 둔다
struct.pack_into('<H', out, 0x15E, ndspy._common.crc16(bytes(out[:0x15E])))
re = NintendoDSRom(bytes(out))
for i in range(n): assert re.files[i] == rom.files[i], i
p = OUT / 'ChibiRobo_B62J_KO_test_R1_moved_fonts_keep80.nds'; p.write_bytes(bytes(out))
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
shutil.copy2(p, Path(buf.value) / p.name); print('MD5', hashlib.md5(bytes(out)).hexdigest())
