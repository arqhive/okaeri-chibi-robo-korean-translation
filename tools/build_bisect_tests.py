"""실기(3DS + TWiLight Menu++) 하우스 밖 Data Abort 원인 가르기용 대조판(2026-11-11). 원본은 문제없고, 코드 문자열 뺀 판도 같은 오류.
- A_text: 대사·글꼴(fulltext_v25) + 조사 패치만. 그림·배너·코드 문자열 없음.
- B_gfx : 그림(2D v22 + 3D v01)만. 대사·글꼴·조사 패치·배너·코드 문자열 없음.
결과는 work/output-bisect/ 와 바탕화면(이름에 A_text·B_gfx)."""
from pathlib import Path
import json, hashlib, ctypes, shutil, sys
from ndspy.rom import NintendoDSRom
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hangul_probe import build
from particle_b62j import apply_to_rom
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
def read(p): return json.loads((ROOT / p).read_text('utf8'))
def sha(b): return hashlib.sha256(b).hexdigest()
o = read('metadata/originals.json')['roms'][0]; source = (ROOT / o['file']).read_bytes(); assert sha(source) == o['sha256']
text = read('metadata/fulltext_build_v25.json'); TR = ROOT / 'work/output-fulltext-v25/resources'
r2 = read('metadata/graphics_2d_build_v22.json'); r3 = read('metadata/graphics_3d_build_v01.json')
G2 = ROOT / 'work/output-graphics-v38/resources'; G3 = ROOT / 'work/output-graphics-v01/resources'
rom = NintendoDSRom(source)
textrep = {r['file']: (TR / r['file']).read_bytes() for r in text['replacements']}
gfxrep = {}
for rec, folder in [(r, G2) for r in r2['replacements']] + [(r, G3) for r in r3['replacements']]:
    d = (folder / rec['file']).read_bytes(); assert sha(d) == rec['sha256']
    if d != rom.files[rom.filenames.idOf(rec['file'])]: gfxrep[rec['file']] = d
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
for name, reps, particle in (('A_text', textrep, True), ('B_gfx', gfxrep, False)):
    built, records = build(source, reps)
    if particle: built, info = apply_to_rom(built, text['particles'])
    p = OUT / f'ChibiRobo_B62J_KO_test_{name}.nds'; p.write_bytes(built)
    d = Path(buf.value) / p.name; shutil.copy2(p, d)
    print(name, '바꾼 파일', len(reps), '조사 패치', particle, 'MD5', hashlib.md5(built).hexdigest(), d)
