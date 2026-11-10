"""graphics_v08: fulltext_v04 + graphics 2D v06 (G0033 cell 23/24 시간·랭킹 aligned with cell 12, popup shadow kept) + 3D v01. Desktop: fixed name ChibiRobo_B62J_KO.nds."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v08';NAME='ChibiRobo_B62J_KO_graphics_v08.nds';DESKNAME='ChibiRobo_B62J_KO.nds'
G2D=ROOT/'work/output-graphics-v08';G3D=ROOT/'work/output-graphics-v01';TEXTRES=ROOT/'work/output-fulltext-v04/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v04.json');assert text['version']=='fulltext_v04';assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v06.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==642  # v06: 파일 칸 이름표 5장 추가(637+5)
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(TEXTRES/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v04'))
 for rec in r2['replacements']+r3['replacements']:
  folder=G2D if rec in r2['replacements'] else G3D
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_2d_v06'))
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 # Compared with graphics_v07 ROM, only the intended graphics file may differ.
 v07=NintendoDSRom((ROOT/'work/output-graphics-v07/ChibiRobo_B62J_KO_graphics_v07.nds').read_bytes())
 diff=sorted(n for n,d in replacements.items() if d!=v07.files[v07.filenames.idOf(n)])
 assert diff==['2d/MainScTitle2.NCGR'],diff
 result,records=build(source,replacements);target=OUT/NAME
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 for name,data in replacements.items():assert reread.files[reread.filenames.idOf(name)]==data,name
 manifest=dict(version='graphics_v08',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v04',base_text_sha256=text['sha256'],base_graphics_version='graphics_2d_v06',changed_from_graphics_v07=diff,source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v04' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_2d_v06' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,only_intended_files_changed_from_v07=True,header_crc16_verified=True,emulator_boot_verified=False,runtime_verified=False,notes=['Change from v07: G0033 cell 23/24 (popup composites) 시간·랭킹 moved to exactly the cell 12 position (+27,+25 / -45,+25) so the cell 12 bottom row underneath no longer shows as "_"; popup shadow rows restored.'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/DESKNAME
 shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v08.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text('''어서와! 치비로보! 한글 그래픽 테스트 v08

실행 파일: NAME_ (바탕화면에는 ChibiRobo_B62J_KO.nds 고정 이름으로 덮어씀, 세이브 이어 쓰기)
v07에서 바뀐 점:
- 파일 고르는 화면에서 버튼이 뜰 때 「_랭킹」처럼 보이던 것 고침: 말풍선 그림(cell 23·24)의 시간·랭킹을 버튼 없을 때(cell 12)와 같은 자리로.
- 시간·랭킹 위 말풍선 그림자 이어 붙임.

게임 부팅·전체 화면 표시 검증: 아직 미실시.
SHA-256: SHA_
'''.replace('NAME_',NAME).replace('SHA_',sha(result)),'utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_v08_built_runtime_pending';j['checks'].update(fulltext_build='metadata/fulltext_build_v04.json',fulltext_layout='metadata/fulltext_layout_v04.json',graphics_build='metadata/graphics_build_v08.json',graphics_runtime_verified=False);j['graphics_review_workflow'].update(output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v08 게임 실행·화면 확인(DS 모드). 바탕화면 롬 이름은 ChibiRobo_B62J_KO.nds 고정.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v08.md').write_text(f'''# 그래픽 포함 테스트 ROM v08

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}` (고정 이름, 세이브 이어 쓰기)
SHA-256: `{sha(result)}`

v07에서 바뀐 것: 파일 고르는 화면 G0033 cell 23·24(말풍선+시간·랭킹 구운 그림).

- 버튼이 뜨면 게임은 cell 23/24를 cell 12(시간·랭킹 글자) 위에 겹쳐 그린다. cell 23/24는 글자 맨 아랫줄이 칸 밖(40행)이라 그 줄은 아래 cell 12가 채운다.
- 한글판은 cell 23/24 글자가 cell 12보다 8px 오른쪽·1px 위라서, cell 12 「랭킹」 맨 아랫줄 검은 테두리가 「_」처럼 드러났다.
- cell 12 글자를 그대로 cell 23은 (+27,+25), cell 24는 (-45,+25) 자리에 붙였다(원본 일본어 글자 위치 기준). 옛 글자 자리는 같은 줄의 원래 색으로 채워 말풍선 그림자 두 줄도 이어진다.
- 작업: `work/graphics-draft/rank-align/align_rank.py`, 이전 판 `rank-align/before/`.

v07 ROM과 비교해 바뀐 자원: {', '.join(diff)}.

에뮬레이터 부팅·게임 화면 검증은 아직 하지 않았다.
''','utf8')
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
