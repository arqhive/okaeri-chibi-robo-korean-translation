"""대조판 3단계(2026-11-11): A1(대사·글꼴, 조사 패치 없음)도 오류. 글꼴과 대사 파일을 나눈다.
- A3_fonts_only: 글꼴 4개만.
- A4_bmg_only  : 대사 BMG만(글꼴 원본이라 한글은 깨져 보임)."""
from pathlib import Path
import json, hashlib, ctypes, shutil, sys
from ndspy.rom import NintendoDSRom
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hangul_probe import build
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
def read(p): return json.loads((ROOT / p).read_text('utf8'))
def sha(b): return hashlib.sha256(b).hexdigest()
o = read('metadata/originals.json')['roms'][0]; source = (ROOT / o['file']).read_bytes(); assert sha(source) == o['sha256']
rom = NintendoDSRom(source)
text = read('metadata/fulltext_build_v25.json'); TR = ROOT / 'work/output-fulltext-v25/resources'
textrep = {r['file']: (TR / r['file']).read_bytes() for r in text['replacements']}
for n, b in sorted(textrep.items()):
    print(f'{n:22s} 원본 {len(rom.files[rom.filenames.idOf(n)]):7d} 한글 {len(b):7d}')
fonts = {n: b for n, b in textrep.items() if n.endswith('.NFTR')}; bmg = {n: b for n, b in textrep.items() if n.endswith('.bmg')}
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
for name, reps in (('A3_fonts_only', fonts), ('A4_bmg_only', bmg)):
    built, records = build(source, reps)
    p = OUT / f'ChibiRobo_B62J_KO_test_{name}.nds'; p.write_bytes(built)
    shutil.copy2(p, Path(buf.value) / p.name)
    print(name, '바꾼 파일', len(reps), 'MD5', hashlib.md5(built).hexdigest())
