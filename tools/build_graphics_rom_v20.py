"""graphics_v20: fulltext_v13 (공백 폭·대사 4줄) + graphics 2D v13 (아이콘 그림 VRAM 1024조각 한도) (옷 아이콘 라벨 10칸·타입→형 8칸) + 3D v01 + 조사 자동 선택 ARM9 패치(particle_b62j). Desktop: fixed name ChibiRobo_B62J_KO.nds."""
from pathlib import Path
import json,hashlib,ctypes,shutil
from ndspy.rom import NintendoDSRom
from build_hangul_probe import build
from particle_b62j import apply_to_rom
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/output-graphics-v20';NAME='ChibiRobo_B62J_KO_graphics_v20.nds';DESKNAME='ChibiRobo_B62J_KO.nds'
G2D=ROOT/'work/output-graphics-v20';G3D=ROOT/'work/output-graphics-v01';TEXTRES=ROOT/'work/output-fulltext-v13/resources'
def read(p):return json.loads((ROOT/p).read_text('utf8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 original=read('metadata/originals.json')['roms'][0];sourcepath=ROOT/original['file'];source=sourcepath.read_bytes();assert sha(source)==original['sha256'];rom=NintendoDSRom(source)
 text=read('metadata/fulltext_build_v13.json');assert text['version']=='fulltext_v13';assert sha((ROOT/text['output']).read_bytes())==text['sha256'];assert sha((ROOT/'translations/entries.json').read_bytes())==text['translation_sha256']
 r2=read('metadata/graphics_2d_build_v13.json');r3=read('metadata/graphics_3d_build_v01.json');assert not r2['errors'];assert len(r2['groups'])==198 and r3['approved_assets']==15
 approved=sum(g.get('approved_cells',0)+g.get('approved_screens',0) for g in r2['groups'])+r3['approved_assets'];assert approved==682  # v12: 얼마야 머신 결과 15칸(667+15)
 checks=[dict(group=g['group'],cell=c) for g in r2['groups'] for c in g.get('game_check_cells',[])];assert checks==[dict(group='G0027',cell=10)]
 replacements={};for_source=[]
 for rec in text['replacements']:
  data=(TEXTRES/rec['file']).read_bytes();assert sha(data)==rec['sha256'];replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='fulltext_v13'))
 for rec in r2['replacements']+r3['replacements']:
  folder=G2D if rec in r2['replacements'] else G3D
  data=(folder/'resources'/rec['file']).read_bytes();assert sha(data)==rec['sha256'];fid=rom.filenames.idOf(rec['file']);assert fid is not None
  if data!=rom.files[fid]:replacements[rec['file']]=data;for_source.append(dict(file=rec['file'],source='graphics_2d_v13'))
 prior=NintendoDSRom((ROOT/text['output']).read_bytes())
 for rec in text['replacements']:assert replacements[rec['file']]==prior.files[prior.filenames.idOf(rec['file'])]
 # Compared with graphics_v08 ROM, only text resources (fonts·BMG) may differ; graphics identical.
 v19=NintendoDSRom((ROOT/'work/output-graphics-v19/ChibiRobo_B62J_KO_graphics_v19.nds').read_bytes())
 diff=sorted(n for n,d in replacements.items() if d!=v19.files[v19.filenames.idOf(n)])
 textfiles={rec['file'] for rec in text['replacements']}|{'2d/MainScIcon2.NCGR','2d/MainScIcon2.NCER'};assert diff and set(diff)<=textfiles and '2d/MainScIcon2.NCGR' in diff and 'Font_normal.NFTR' in diff,diff

 built,records=build(source,replacements)
 result,particle=apply_to_rom(built,text['particles']);target=OUT/NAME
 assert particle['secure_area_unchanged']
 if target.exists():assert target.read_bytes()==result,'Different existing build: use a new version'
 else:target.write_bytes(result)
 assert sha(target.read_bytes())==sha(result);assert sha(sourcepath.read_bytes())==original['sha256'];assert len(result)==len(source)==67108864
 reread=NintendoDSRom(target.read_bytes());assert len(reread.files)==4005
 assert reread.files==NintendoDSRom(built).files
 for name,data in replacements.items():assert reread.files[reread.filenames.idOf(name)]==data,name
 manifest=dict(version='graphics_v20',output=str(target.relative_to(ROOT)),sha256=sha(result),size_bytes=len(result),base_text_version='fulltext_v13',base_text_sha256=text['sha256'],base_graphics_version='graphics_2d_v13',changed_from_graphics_v19=diff,particle_patch=particle,source_sha256=original['sha256'],translated_messages=text['translated_messages'],fonts=len(text['fonts']),approved_graphics_inserted=approved,game_check_graphics=checks,composition_pending_original_preserved=27,resource_files_changed=len(records),text_resources=sum(x['source']=='fulltext_v13' for x in for_source),graphics_resource_files=sum(x['source']=='graphics_2d_v13' for x in for_source),replacements=records,source_unchanged=True,rom_readback_verified=True,only_intended_changed_from_v19=True,header_crc16_verified=True,emulator_boot_verified=False,runtime_verified=False,notes=['Change from v19: text fulltext_v13 (half-width space advance = half of full-width space in 4 fonts; 4 dialogue lines); graphics 2D v13 (G0025 MainScIcon2 kept within the 1024-tile OBJ VRAM slot seen in save state ml4: shared 32x32 frames untouched, overflow pixels on added 8x16 objects).'])
 buf=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buf)==0;desktop=Path(buf.value)/DESKNAME
 shutil.copy2(target,desktop)
 assert sha(desktop.read_bytes())==sha(result);manifest.update(desktop_copy=str(desktop),desktop_copy_hash_verified=True)
 (ROOT/'metadata/graphics_build_v20.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 (OUT/'SHA256.txt').write_text(sha(result)+'  '+NAME+'\n','ascii')
 (OUT/'README-ko.txt').write_text('''어서와! 치비로보! 한글 테스트 v20

실행 파일: NAME_ (바탕화면에는 ChibiRobo_B62J_KO.nds 고정 이름으로 덮어씀, 세이브 이어 쓰기)
v19에서 바뀐 점:
- 옷·치비 메뉴 아이콘 테두리와 이름이 깨지던 것 고침.
- 낱말 사이 띄어쓰기 간격을 넓힘.
- 대사 몇 줄 다듬기.

게임 실행 검증: 아직 미실시.
SHA-256: SHA_
'''.replace('NAME_',NAME).replace('SHA_',sha(result)),'utf8')
 p=ROOT/'project.json';j=read('project.json');j['status']='graphics_v20_built_runtime_pending';j['checks'].update(fulltext_build='metadata/fulltext_build_v13.json',graphics_build='metadata/graphics_build_v20.json',graphics_runtime_verified=False,particle_runtime_verified=False);j['graphics_review_workflow'].update(output_rom=str(target.relative_to(ROOT)));j['next_work']='graphics_v20 게임 실행 확인: 저장할 때 멈추지 않는지(조사 패치 포함 정식 롬), 조사 자동 선택, 복사·이어하기 버튼 글자 위치. 바탕화면 롬 이름은 ChibiRobo_B62J_KO.nds 고정.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 (ROOT/'docs/graphics-build-v20.md').write_text(f'''# 한글 테스트 ROM v20

파일: `{target.relative_to(ROOT)}`
바탕화면: `{desktop}` (고정 이름, 세이브 이어 쓰기)
SHA-256: `{sha(result)}`

v19에서 바뀐 것: 대사 fulltext_v13, 그림 2D v13.

- 반각 공백 폭 1px → 전각 공백 폭의 절반(large 6, normal 4, small 3, smallsmall 2).
- MainScIcon2(G0025): 세이브 스테이트(ml4)로 OBJ VRAM에 0~1023 조각만 올라감을 확인. 공유 32x32 테두리는 건드리지 않고 넘치는 픽셀은 8x16 조각을 덧붙여 1024조각 안에 맞춤(`tools/build_graphics_2d_v13.py`). 174 칫솔 +1px, 「형」 칸 (17,11) 원본 1점.
- 대사: 톤피 #405 「자,」 지움, 경찰 #131 「있네?」, #136 「그게…」, 상어 #77 「꿀꺽해서 미안하니까」.
- 조사 패치는 v19와 같다. v19와 다른 자원: {', '.join(diff)}.

게임 실행 검증은 아직.
''','utf8')
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('replacements','notes')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
