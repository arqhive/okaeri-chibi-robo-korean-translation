"""저장 멈춤 가르기용 시험 롬 3: 시험 롬 1(조사 패치 뺀 v11)에서 MsgResTonpy.bmg만 원본으로 되돌린다(2026-11-08). 시험 롬 2(BMG 전부 원본)는 정상 저장됐다.
시험 롬 1은 원판과 달리 저장 중 톤피 tp_search 애니메이션을 롬에서 읽다 카드 잠금에 걸려 멈췄다.
v11은 저장 뒤 백업 카드 잠금이 안 풀려 멈춘다. 이 롬에서도 멈추면 조사 패치 탓이 아니다.
조사 표시 문자는 폭 0 빈 글자라 이 롬에서는 조사(을/를 등)가 안 보인다."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-test-tonpy-original';NAME='ChibiRobo_B62J_KO_v11_tonpy_original.nds';DESKNAME='ChibiRobo_B62J_KO.nds'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];source=(ROOT/original['file']).read_bytes();assert sha(source)==original['sha256']
 v11=NintendoDSRom((ROOT/'work/output-graphics-v11/ChibiRobo_B62J_KO_graphics_v11.nds').read_bytes());orig=NintendoDSRom(source)
 # v11의 파일 중 원본과 다른 것을 그대로 가져온다(대사·글꼴·그림). ARM9·오버레이 표·헤더는 원본 그대로.
 replacements={}
 for i,data in enumerate(v11.files):
  n=v11.filenames.filenameOf(i) or ''
  if data!=orig.files[i] and n!='MsgResTonpy.bmg':replacements[n]=data
 result,records=build(source,replacements)
 r=NintendoDSRom(result)
 assert all((r.files[i]==orig.files[i]) if (r.filenames.filenameOf(i) or '')=='MsgResTonpy.bmg' else (r.files[i]==v11.files[i]) for i in range(len(r.files)))
 assert r.arm9==orig.arm9 and r.arm9OverlayTable==orig.arm9OverlayTable and result[0x50:0x58]==source[0x50:0x58],'code must be original'
 (OUT/NAME).write_bytes(result)
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/DESKNAME
 shutil.copy2(OUT/NAME,desktop);assert sha(desktop.read_bytes())==sha(result)
 print(json.dumps(dict(output=str((OUT/NAME).relative_to(ROOT)),sha256=sha(result),replaced_files=len(replacements),desktop=str(desktop)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
