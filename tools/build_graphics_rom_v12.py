"""graphics_v12: fulltext_v08 (톤피 #231 저장 멈춤 수정·키스 뵤→우) + graphics 2D v07 + 3D v01 + 조사 자동 선택 ARM9 패치(particle_b62j). Desktop: fixed name ChibiRobo_B62J_KO.nds."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
from particle_b62j import apply_to_rom
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v12';NAME='ChibiRobo_B62J_KO_graphics_v12.nds';DESKNAME='ChibiRobo_B62J_KO.nds'
G2D=ROOT/'work/output-graphics-v11';G3D=ROOT/'work/output-graphics-v01';TEXTRES=ROOT/'work/output-fulltext-v08/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v08.json');assert text['version']=='fulltext_v08';assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v07.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==642  # v06: 파일 칸 이름표 5장 추가(637+5)
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(TEXTRES/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v08'))
 for rec in r2['replacements']+r3['replacements']:
  folder=G2D if rec in r2['replacements'] else G3D
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_2d_v07'))
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 # Compared with graphics_v08 ROM, only text resources (fonts·BMG) may differ; graphics identical.
 v11=NintendoDSRom((ROOT/'work/output-graphics-v11/ChibiRobo_B62J_KO_graphics_v11.nds').read_bytes())
 diff=sorted(n for n,d in replacements.items() if d!=v11.files[v11.filenames.idOf(n)])
 textfiles={rec['file'] for rec in text['replacements']};assert diff and set(diff)<=textfiles,diff

 built,records=build(source,replacements)
 result,particle=apply_to_rom(built,text['particles']);target=OUT/NAME
 assert particle['secure_area_unchanged']
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 assert reread.files==NintendoDSRom(built).files
 for name,data in replacements.items():assert reread.files[reread.filenames.idOf(name)]==data,name
 manifest=dict(version='graphics_v12',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v08',base_text_sha256=text['sha256'],base_graphics_version='graphics_2d_v07',changed_from_graphics_v11=diff,particle_patch=particle,source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v08' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_2d_v07' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,only_text_files_changed_from_v11=True,header_crc16_verified=True,emulator_boot_verified=False,runtime_verified=False,notes=['Change from v11: text fulltext_v08 (MsgResTonpy#231 total 9 characters kept to avoid the save freeze; Keith verbal tic 뵤→우).'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/DESKNAME
 shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v12.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text('''어서와! 치비로보! 한글 테스트 v12

실행 파일: NAME_ (바탕화면에는 ChibiRobo_B62J_KO.nds 고정 이름으로 덮어씀, 세이브 이어 쓰기)
v11에서 바뀐 점:
- 저장할 때 게임이 멈추던 것 고침(톤피 「렛츠 저장!」 대사 글자 수를 원문에 맞춤).
- 키스 말버릇 「뵤」→「우」.

게임 실행 검증: 아직 미실시.
SHA-256: SHA_
'''.replace('NAME_',NAME).replace('SHA_',sha(result)),'utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_v12_built_runtime_pending';j['checks'].update(fulltext_build='metadata/fulltext_build_v08.json',graphics_build='metadata/graphics_build_v12.json',graphics_runtime_verified=False,particle_runtime_verified=False);j['graphics_review_workflow'].update(output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v12 게임 실행 확인: 저장할 때 멈추지 않는지(조사 패치 포함 정식 롬), 조사 자동 선택, 복사·이어하기 버튼 글자 위치. 바탕화면 롬 이름은 ChibiRobo_B62J_KO.nds 고정.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v12.md').write_text(f'''# 한글 테스트 ROM v12

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}` (고정 이름, 세이브 이어 쓰기)
SHA-256: `{sha(result)}`

v11에서 바뀐 것: 대사 fulltext_v08.

- 저장 멈춤 수정: MsgResTonpy.bmg#231 전체 글자 수를 원문과 같은 9자로(「　렛츠<제어>　저장！　 」). 짧으면 저장 중 톤피 애니메이션을 롬에서 읽다가 카드 잠금과 겹쳐 멈춘다. 시험 롬 1~9로 가름.
- 키스 말버릇 뵤→우 73줄, 4줄 다듬기.
- 그림·조사 패치는 v11과 같다. v11과 다른 자원: {', '.join(diff)}.

게임 실행 검증은 아직.
''','utf8')
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
