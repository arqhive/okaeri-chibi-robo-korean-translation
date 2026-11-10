"""graphics_v07: fulltext_v04 (Hangul glyph placement v2) + graphics 2D v05 + 3D v01. Desktop: fixed name ChibiRobo_B62J_KO.nds."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v07';NAME='ChibiRobo_B62J_KO_graphics_v07.nds';DESKNAME='ChibiRobo_B62J_KO.nds'
G2D=ROOT/'work/output-graphics-v06';G3D=ROOT/'work/output-graphics-v01';TEXTRES=ROOT/'work/output-fulltext-v04/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v04.json');assert text['version']=='fulltext_v04';assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v05.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==642  # v06: 파일 칸 이름표 5장 추가(637+5)
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(TEXTRES/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v04'))
 for rec in r2['replacements']+r3['replacements']:
  folder=G2D if rec in r2['replacements'] else G3D
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_2d_v05'))
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 # Compared with graphics_v06 ROM, only the four fonts may differ.
 v06=NintendoDSRom((ROOT/'work/output-graphics-v06/ChibiRobo_B62J_KO_graphics_v06.nds').read_bytes())
 diff=sorted(n for n,d in replacements.items() if d!=v06.files[v06.filenames.idOf(n)])
 assert len(diff)==4 and all(n.endswith('.NFTR') for n in diff),diff
 result,records=build(source,replacements);target=OUT/NAME
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 for name,data in replacements.items():assert reread.files[reread.filenames.idOf(name)]==data,name
 manifest=dict(version='graphics_v07',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v04',base_text_sha256=text['sha256'],base_graphics_version='graphics_2d_v05',changed_from_graphics_v06=diff,source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v04' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_2d_v05' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,only_intended_files_changed_from_v06=True,header_crc16_verified=True,emulator_boot_verified=False,runtime_verified=False,notes=['Change from v06: Hangul glyphs re-inserted into the 4 general fonts with hangul_font_v2 (common top line, per-glyph left/ink width/font advance). BMG and graphics unchanged.'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/DESKNAME
 shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v07.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text('''어서와! 치비로보! 한글 그래픽 테스트 v07

실행 파일: NAME_ (바탕화면에는 ChibiRobo_B62J_KO.nds 고정 이름으로 덮어씀, 세이브 이어 쓰기)
v06에서 바뀐 점:
- 대사 글꼴 4종의 한글 글자 배치를 고침: 글자 윗줄을 하나로 맞추고, 간격을 갈무리 원래 폭(한자와 같은 12px 등)으로.
  예전엔 글자마다 아래 끝을 맞추고 폭을 칸 폭으로 고정해 들쭉날쭉했음.
- 대사·그림은 v06과 같음.

게임 부팅·전체 화면 표시 검증: 아직 미실시.
SHA-256: SHA_
'''.replace('NAME_',NAME).replace('SHA_',sha(result)),'utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_v07_built_runtime_pending';j['checks'].update(fulltext_build='metadata/fulltext_build_v04.json',fulltext_layout='metadata/fulltext_layout_v04.json',graphics_build='metadata/graphics_build_v07.json',graphics_runtime_verified=False);j['graphics_review_workflow'].update(output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v07 게임 실행·화면 확인(DS 모드). 바탕화면 롬 이름은 ChibiRobo_B62J_KO.nds 고정.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v07.md').write_text(f'''# 그래픽 포함 테스트 ROM v07

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}` (고정 이름, 세이브 이어 쓰기)
SHA-256: `{sha(result)}`

v06에서 바뀐 것: 대사 글꼴 4종(Font_large·normal·small·smallsmall)의 한글 글자 넣는 방식.

- 예전(`prepare_hangul_probe.expand`): 글자마다 잉크 아래 끝을 칸 바닥에 붙이고 칸 가운데에 둠, 폭 정보 (0,w,w) 고정. 받침 없는 글자가 1px 내려가고 간격이 한자보다 1px 좁고 들쭉날쭉했다.
- 지금(`tools/hangul_font_v2.py`): 같은 펜 위치에서 그려 글꼴 전체 잉크 윗줄을 칸 0행에 맞춤, 폭 정보는 (왼쪽 여백, 잉크 폭, 글꼴 advance).
- 대사 자원: fulltext_v04(`tools/build_full_text_v04.py`). 대사 내용은 v03과 같다.
- 줄 길이: 대사 파일별 원문 최대 줄 폭을 넘는 대사는 MsgResGeo#81 한 줄(173>172px). 256px 초과 없음.

v06 ROM과 비교해 바뀐 자원: {', '.join(diff)}.

에뮬레이터 부팅·게임 화면 검증은 아직 하지 않았다.
''','utf8')
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
