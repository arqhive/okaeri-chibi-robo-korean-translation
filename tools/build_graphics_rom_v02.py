"""Combine verified Korean text/fonts and approved graphics into a test ROM."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v02';NAME='ChibiRobo_B62J_KO_graphics_v02.nds'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v01.json');assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v02.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==637
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(ROOT/'work/output-fulltext/resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v01'))
 for rec in r2['replacements']+r3['replacements']:
  folder=OUT if rec in r2['replacements'] else ROOT/'work/output-graphics-v01'
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_v02'))
 # Assert text/font bytes equal the previous full-text ROM, not only source files.
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 result,records=build(source,replacements);target=OUT/NAME
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 # Approved and retained classifications are kept separate from insertion state.
 manifest=dict(version='graphics_v02',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v01',base_text_sha256=text['sha256'],source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,graphics_2d_groups=198,graphics_3d_assets=15,texture_occurrences=16,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v01' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_v02' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,graphics_decode_readback_verified=True,non_target_files_byte_identical=True,code_overlay_tables_banner_fnt_preserved=True,header_crc16_verified=True,original_palette_preserved=True,emulator_boot_verified=False,runtime_verified=False,notes=['637 approved graphic asset references inserted, plus G0027/cell/10 as previously requested in-game-check draft.','27 unresolved composition fragments remain original.','Text/fonts are byte-identical to fulltext_v01; in-game full-text layout is unverified.'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/NAME
 if desktop.exists():assert desktop.read_bytes()==result,'Different desktop file: do not overwrite'
 else:shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v02.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text(f'''어서와! 치비로보! 한글 그래픽 테스트 v02

실행 파일: {NAME}
본문: 7,095개 번역 + 기존 확장 한글 폰트 4종
그림: 검토 승인 자원 637개 + 게임 확인용 없음 표시 1개
미확정 UI 조각 27개: 원본 유지

정적 검사: 원본 ROM 불변, 파일 읽기 재검증, 그래픽 재디코딩 비교, 팔레트 보존, 헤더 CRC 통과.
게임 부팅·전체 화면 표시 검증: 아직 미실시.

확인 지점: 타이틀, 저장 메뉴, 상품 카드, 홈쇼핑 안내, 치비로보 소지품/없음, 결과 표시.
SHA-256: {sha(result)}
''','utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_test_rom_v01_built_runtime_pending';j['checks'].update(graphics_build='metadata/graphics_build_v02.json',graphics_2d_build='metadata/graphics_2d_build_v02.json',graphics_3d_build='metadata/graphics_3d_build_v01.json',graphics_rom_readback_verified=True,graphics_runtime_verified=False);j['graphics_review_workflow'].update(rom_inserted=True,inserted_approved_assets=637,inserted_game_check_assets=1,output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v02 게임 실행·화면 확인. G0027/cell/10 없음 및 UI 조각 27개 실제 표시 조합 확인.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v02.md').write_text(f'''# 그래픽 포함 테스트 ROM v02

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}`
SHA-256: `{sha(result)}`
크기: 64 MiB

fulltext_v01의 본문 7,095개와 한글 폰트 4개를 그대로 유지하고 승인 그래픽 자원 참조 637개를 삽입했다. G0027/10 없음은 이전 게임 확인 요청에 따라 현재 PNG를 추가 삽입했으며 승인 상태를 바꾸지 않았다. UI 조각 27개는 원본 상태를 유지한다.

2D 198개 그룹은 NCGR/NCER/NSCR로 변환 후 재디코딩하여 승인 PNG와 비교했다. 모든 목표 픽셀을 원본 팔레트로 정확히 표현했다. 서로 다른 결과가 공유 타일을 요구하는 경우 OAM 참조를 분리했고, 모든 미대상 셀은 디코딩 결과가 원본과 같다. 글자가 원래 OAM 영역 사이 빈틈에 걸친 2개 그룹에는 동일 위치·아핀 설정의 투명 8×8 OAM을 추가해 획을 담았다. OAM 타일 주소와 128 KiB 한도를 확인했다. 이 구조 확장은 게임에서 추가 확인이 필요하다.

3D 15개 자원(16회 사용)은 기존 텍스처 픽셀 데이터만 교체하고 모델·UV·팔레트·다른 텍스처 바이트를 그대로 유지했다. 결과 픽셀과 승인 PNG가 정확히 일치한다.

검증된 원본의 FF 패딩에 변경 자원을 추가하고 FAT/사용 크기/헤더 CRC만 갱신했다. 코드·오버레이·배너·FNT 및 비대상 파일은 원본과 일치한다. 전체 파일을 ROM에서 다시 읽어 해시를 확인했다. 바탕화면 복사본도 동일하다.

에뮬레이터 부팅 및 모든 게임 화면 검증은 미실시. 기존 v03 한글 출력 사용자 확인을 이번 전체 빌드 검증으로 간주하지 않는다.
''','utf8')
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
