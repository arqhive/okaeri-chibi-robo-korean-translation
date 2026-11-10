"""대조판 2단계(2026-11-11): A_text(대사·글꼴+조사 패치)도 하우스 밖 오류. 그 안을 나눈다.
- A1_text_noparticle: 대사·글꼴만, 조사 패치 없음(ARM9 원본).
- A2_particle_only: 원본 + 조사 패치만(대사·글꼴 원본)."""
from pathlib import Path
import json, hashlib, ctypes, shutil, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hangul_probe import build
from particle_b62j import apply_to_rom
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
def read(p): return json.loads((ROOT / p).read_text('utf8'))
def sha(b): return hashlib.sha256(b).hexdigest()
o = read('metadata/originals.json')['roms'][0]; source = (ROOT / o['file']).read_bytes(); assert sha(source) == o['sha256']
text = read('metadata/fulltext_build_v25.json'); TR = ROOT / 'work/output-fulltext-v25/resources'
textrep = {r['file']: (TR / r['file']).read_bytes() for r in text['replacements']}
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
for name, reps, particle in (('A1_text_noparticle', textrep, False), ('A2_particle_only', {}, True)):
    built, records = build(source, reps)
    if particle: built, info = apply_to_rom(built, text['particles'])
    p = OUT / f'ChibiRobo_B62J_KO_test_{name}.nds'; p.write_bytes(built)
    d = Path(buf.value) / p.name; shutil.copy2(p, d)
    print(name, '바꾼 파일', len(reps), '조사 패치', particle, 'MD5', hashlib.md5(built).hexdigest())
