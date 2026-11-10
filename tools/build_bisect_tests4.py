"""대조판 4단계(2026-11-11): 글꼴만 넣은 판(A3)도 하우스 밖 오류. 크기 때문인지(메모리 부족) 내용 때문인지 가른다.
- A5_padded_fonts: 원본 글꼴 4개 뒤에 0을 붙여 한글 글꼴과 같은 크기로(글자는 원본 그대로). 이게 오류면 크기(메모리) 문제."""
from pathlib import Path
import json, hashlib, ctypes, shutil, sys
from ndspy.rom import NintendoDSRom
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hangul_probe import build
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
def read(p): return json.loads((ROOT / p).read_text('utf8'))
o = read('metadata/originals.json')['roms'][0]; source = (ROOT / o['file']).read_bytes()
rom = NintendoDSRom(source); TR = ROOT / 'work/output-fulltext-v25/resources'
reps = {}
for n in ('Font_large.NFTR', 'Font_normal.NFTR', 'Font_small.NFTR', 'Font_smallsmall.NFTR'):
    orig = rom.files[rom.filenames.idOf(n)]; ko = (TR / n).read_bytes()
    reps[n] = orig + bytes(len(ko) - len(orig)); print(n, len(orig), '→', len(reps[n]))
built, records = build(source, reps)
p = OUT / 'ChibiRobo_B62J_KO_test_A5_padded_fonts.nds'; p.write_bytes(built)
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
shutil.copy2(p, Path(buf.value) / p.name); print('MD5', hashlib.md5(built).hexdigest())
