"""graphics_v03: fulltext_v02 text/fonts + the unchanged graphics_v02 2D/3D resources."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v03';NAME='ChibiRobo_B62J_KO_graphics_v03.nds'
G2D=ROOT/'work/output-graphics-v02';G3D=ROOT/'work/output-graphics-v01';TEXTRES=ROOT/'work/output-fulltext-v02/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v02.json');assert text['version']=='fulltext_v02';assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v02.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==637
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(TEXTRES/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v02'))
 for rec in r2['replacements']+r3['replacements']:
  folder=G2D if rec in r2['replacements'] else G3D
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_v02'))
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 # Graphics bytes must equal the previous integrated ROM; only text/fonts may differ.
 v02=NintendoDSRom((G2D/'ChibiRobo_B62J_KO_graphics_v02.nds').read_bytes())
 for name,data in replacements.items():
  if not name.endswith(('.bmg','.NFTR')):assert data==v02.files[v02.filenames.idOf(name)],name
 result,records=build(source,replacements);target=OUT/NAME
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 for name,data in replacements.items():assert reread.files[reread.filenames.idOf(name)]==data,name
 manifest=dict(version='graphics_v03',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v02',base_text_sha256=text['sha256'],base_graphics_version='graphics_v02',source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v02' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_v02' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,graphics_bytes_identical_to_v02=True,header_crc16_verified=True,emulator_boot_verified=False,runtime_verified=False,notes=['Change from v02: fullwidth percent restored in 12 messages (MsgResSys#380/#425/#525, Tonpy#95/#160/#240/#495/#594, Family3#375, Gho#617, Ibe#150/#154).','Graphics resources are byte-identical to graphics_v02.'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/NAME
 if desktop.exists():assert desktop.read_bytes()==result,'Different desktop file: do not overwrite'
 else:shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v03.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text(f'''어서와! 치비로보! 한글 그래픽 테스트 v03

실행 파일: {NAME}
v02에서 바뀐 점: 퍼센트 기호 12줄을 원문처럼 전각 ％로 되돌림(printf 서식 오해 방지).
그림·3D 자원은 v02와 바이트 단위로 같음.

게임 부팅·전체 화면 표시 검증: 아직 미실시.
SHA-256: {sha(result)}
''','utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_v03_built_runtime_pending';j['checks'].update(graphics_build='metadata/graphics_build_v03.json',fulltext_build='metadata/fulltext_build_v02.json',fulltext_layout='metadata/fulltext_layout_v02.json',graphics_runtime_verified=False);j['graphics_review_workflow'].update(output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v03 게임 실행·화면 확인(DS 모드). 홈쇼핑·메인 아이콘·정비 화면 OBJ, 반짝반짝도 % 표시 확인.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v03.md').write_text(f'''# 그래픽 포함 테스트 ROM v03

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}`
SHA-256: `{sha(result)}`

v02에서 퍼센트 기호만 고친 판이다. 번역 원고의 반각 `%` 12곳을 원문과 같은 전각 `％`로 되돌렸다. `%d` 바로 뒤의 반각 `%`는 게임 printf가 서식 문자로 읽을 수 있다. 본문은 fulltext_v02로 다시 빌드했고, 그림·3D 자원은 v02와 바이트 단위로 같다.

에뮬레이터 부팅·게임 화면 검증은 아직 하지 않았다.
''','utf8')
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
