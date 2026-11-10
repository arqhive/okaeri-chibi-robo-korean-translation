"""대조판(헤더 0x80 원본 고정, 2026-11-11). v42(0x80 원본)·T2(오버레이 원래 자리)·T1(코드 문자열 없음)도 하우스 밖 오류.
원본에 한 가지씩만 넣는다. 모두 0x80은 원본 값.
- K1_text : 대사 BMG + 글꼴(fulltext_v25)
- K2_gfx  : 그림(2D v22 + 3D v01)
- K3_part : 조사 패치(ARM9)만
- K4_banner: DS 메뉴 이름(배너)만"""
from pathlib import Path
import json, hashlib, ctypes, shutil, struct, sys
import ndspy._common
from ndspy.rom import NintendoDSRom
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hangul_probe import build
from particle_b62j import apply_to_rom
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
def read(p): return json.loads((ROOT / p).read_text('utf8'))
def sha(b): return hashlib.sha256(b).hexdigest()
o = read('metadata/originals.json')['roms'][0]; source = (ROOT / o['file']).read_bytes(); assert sha(source) == o['sha256']
rom = NintendoDSRom(source); ORIG80 = struct.unpack_from('<I', source, 0x80)[0]
text = read('metadata/fulltext_build_v25.json'); TR = ROOT / 'work/output-fulltext-v25/resources'
textrep = {r['file']: (TR / r['file']).read_bytes() for r in text['replacements']}
r2 = read('metadata/graphics_2d_build_v22.json'); r3 = read('metadata/graphics_3d_build_v01.json')
gfx = {}
for rec, folder in [(r, ROOT / 'work/output-graphics-v38/resources') for r in r2['replacements']] + [(r, ROOT / 'work/output-graphics-v01/resources') for r in r3['replacements']]:
    d = (folder / rec['file']).read_bytes(); assert sha(d) == rec['sha256']
    if d != rom.files[rom.filenames.idOf(rec['file'])]: gfx[rec['file']] = d
def banner(b):
    b = bytearray(b); bo = struct.unpack_from('<I', b, 0x68)[0]; t = '어서와! 치비로보!\n해피리치 대청소!\nNintendo'.encode('utf-16le')
    for i in range(6): b[bo + 0x240 + i * 0x100:bo + 0x340 + i * 0x100] = t.ljust(0x100, b'\0')
    struct.pack_into('<H', b, bo + 2, ndspy._common.crc16(bytes(b[bo + 0x20:bo + 0x840]))); return bytes(b)
def keep80(b):
    b = bytearray(b); struct.pack_into('<I', b, 0x80, ORIG80); struct.pack_into('<H', b, 0x15E, ndspy._common.crc16(bytes(b[:0x15E]))); return bytes(b)
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
for name, reps, part, ban in (('K1_text', textrep, False, False), ('K2_gfx', gfx, False, False), ('K3_part', {}, True, False), ('K4_banner', {}, False, True)):
    built, _ = build(source, reps) if reps else (source, None)
    if part: built, _ = apply_to_rom(built, text['particles'])
    if ban: built = banner(built)
    built = keep80(built); assert struct.unpack_from('<I', built, 0x80)[0] == ORIG80
    p = OUT / f'ChibiRobo_B62J_KO_test_{name}.nds'; p.write_bytes(built); shutil.copy2(p, Path(buf.value) / p.name)
    print(name, '바꾼 파일', len(reps), 'MD5', hashlib.md5(built).hexdigest())
