"""graphics_v04: fulltext_v03 text/fonts + graphics 2D v03 (touch label centered, title logo edits) + 3D v01."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v04';NAME='ChibiRobo_B62J_KO_graphics_v04.nds'
G2D=ROOT/'work/output-graphics-v04';G3D=ROOT/'work/output-graphics-v01';TEXTRES=ROOT/'work/output-fulltext-v03/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v03.json');assert text['version']=='fulltext_v03';assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v03.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==637
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(TEXTRES/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v03'))
 for rec in r2['replacements']+r3['replacements']:
  folder=G2D if rec in r2['replacements'] else G3D
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_2d_v03'))
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 # Compared with graphics_v03 ROM, only the intended files may differ.
 v03=NintendoDSRom((ROOT/'work/output-graphics-v03/ChibiRobo_B62J_KO_graphics_v03.nds').read_bytes())
 diff=sorted(n for n,d in replacements.items() if d!=v03.files[v03.filenames.idOf(n)])
 assert len(diff)==3 and '2d/MainScIcon2.NCGR' in diff and '2d/SubScBGTitle.NCGR' in diff and sum(n.endswith('MsgResSys.bmg') for n in diff)==1,diff
 result,records=build(source,replacements);target=OUT/NAME
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 for name,data in replacements.items():assert reread.files[reread.filenames.idOf(name)]==data,name
 manifest=dict(version='graphics_v04',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v03',base_text_sha256=text['sha256'],base_graphics_version='graphics_2d_v03',changed_from_graphics_v03=diff,source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v03' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_2d_v03' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,only_intended_files_changed_from_v03=True,header_crc16_verified=True,emulator_boot_verified=False,runtime_verified=False,notes=['Change from v03: MsgResSys#720 boot notice periods; G0025 cell 212 touch label centered; title logo G0218 circle/hyphen edits.'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/NAME
 if desktop.exists():assert desktop.read_bytes()==result,'Different desktop file: do not overwrite'
 else:shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v04.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text(f'''어서와! 치비로보! 한글 그래픽 테스트 v04

실행 파일: {NAME}
v03에서 바뀐 점:
- 게임 시작 준비 안내(MsgResSys#720) 두 문장 끝에 마침표.
- 「여기를 터치!」 그림 글씨(G0025 cell 212) 두 그림 사이 가운데 정렬.
- 타이틀 로고(G0218): 어·서 동그라미를 !·- 동그라미에서 복사, 하이픈을 느낌표 윗막대로 교체, 튀는 픽셀 보정.

게임 부팅·전체 화면 표시 검증: 아직 미실시.
SHA-256: {sha(result)}
''','utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_v04_built_runtime_pending';j['checks'].update(graphics_build='metadata/graphics_build_v04.json',fulltext_build='metadata/fulltext_build_v03.json',fulltext_layout='metadata/fulltext_layout_v03.json',graphics_runtime_verified=False);j['graphics_review_workflow'].update(output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v04 게임 실행·화면 확인(DS 모드). 타이틀 로고·여기를 터치 정렬·시작 안내 마침표 확인.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v04.md').write_text(f'''# 그래픽 포함 테스트 ROM v04

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}`
SHA-256: `{sha(result)}`

v03에서 바뀐 것:

- 본문: 게임 시작 준비 안내(MsgResSys#720) 두 문장 끝에 마침표를 넣었다(fulltext_v03).
- 그림: 「여기를 터치!」(G0025 cell 212) 글자를 두 그림 사이 가운데로 옮겼다(`tools/draft_ui_bulk.py` pos=(15,2)).
- 그림: 타이틀 로고 G0218. 어 동그라미는 ! 동그라미, 서 동그라미는 - 동그라미에서 글자 픽셀만 빼고 복사했다. 하이픈은 느낌표 윗막대를 눕혀 가운데 한 줄을 빼서 만들었다. 튀는 픽셀 몇 개를 주변 색으로 맞췄다. 작업 기록은 `work/graphics-draft/title-logo-v1/`의 eo-glyph·seo-glyph·hyphen·pixel-fix.

v03 ROM과 비교해 바뀐 자원은 MsgResSys.bmg, 2d/MainScIcon2.NCGR, 2d/SubScBGTitle.NCGR 세 개뿐이다.

에뮬레이터 부팅·게임 화면 검증은 아직 하지 않았다.
''','utf8')
 old=desktop.parent/'ChibiRobo_B62J_KO_graphics_v03.nds'
 if old.exists():old.unlink();print('바탕화면 이전 롬 삭제',old)
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
