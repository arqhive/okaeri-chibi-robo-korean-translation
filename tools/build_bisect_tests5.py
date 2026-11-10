"""대조판 5단계(2026-11-11): 글꼴 크기 한도 재기. v40(+4.5만)·v41(+2.9만)도 실기 오류.
원본 글꼴(글자 그대로) 4개 뒤에 0을 붙여 합계 +N 바이트로 만든다(글꼴별 원본 크기 비율로 나눔, 4바이트 단위).
- P2K : 합계 약 +2,000
- P10K: 합계 약 +10,000
P2K도 오류면 「글꼴은 원본보다 조금도 커지면 안 되는」 고정 크기 문제, P10K만 통과하면 한도는 1만~2.9만 사이."""
from pathlib import Path
import json, hashlib, ctypes, shutil, sys
from ndspy.rom import NintendoDSRom
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hangul_probe import build
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'work/output-bisect'; OUT.mkdir(exist_ok=True)
o = json.loads((ROOT / 'metadata/originals.json').read_text('utf8'))['roms'][0]; source = (ROOT / o['file']).read_bytes()
rom = NintendoDSRom(source)
names = ('Font_large.NFTR', 'Font_normal.NFTR', 'Font_small.NFTR', 'Font_smallsmall.NFTR')
orig = {n: rom.files[rom.filenames.idOf(n)] for n in names}; tot = sum(len(b) for b in orig.values())
buf = ctypes.create_unicode_buffer(32768); assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0
for tag, extra in (('P2K', 2000), ('P10K', 10000)):
    reps = {n: b + bytes((extra * len(b) // tot) & ~3) for n, b in orig.items()}
    built, _ = build(source, reps)
    p = OUT / f'ChibiRobo_B62J_KO_test_{tag}.nds'; p.write_bytes(built); shutil.copy2(p, Path(buf.value) / p.name)
    print(tag, '합계 증가', sum(len(reps[n]) - len(orig[n]) for n in names), 'MD5', hashlib.md5(built).hexdigest())
