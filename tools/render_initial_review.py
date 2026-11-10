from pathlib import Path
import json,html,hashlib,importlib.metadata
ROOT=Path(__file__).resolve().parents[1]
def main():
 inv=json.loads((ROOT/'metadata/filesystem_inventory.json').read_text(encoding='utf-8'));a=json.loads((ROOT/'metadata/text_font_analysis.json').read_text(encoding='utf-8'));c=json.loads((ROOT/'metadata/code_resources.json').read_text(encoding='utf-8'));entries=json.loads((ROOT/'metadata/text_entries.json').read_text(encoding='utf-8'));out=ROOT/'work/initial-analysis';out.mkdir(exist_ok=True)
 page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>어서와! 치비로보! · 초기 구조 조사</title><style>body{margin:0;background:#f3f2eb;color:#24352d;font:16px/1.7 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:36px 24px}h1{font-size:29px}h2{margin-top:0}.card{background:white;border:1px solid #d7ddd1;border-radius:12px;padding:24px;margin:22px 0}.stats{display:flex;gap:16px;flex-wrap:wrap}.stat{padding:16px 24px;background:#dfebd8;border-radius:10px}.stat b{display:block;font-size:25px}table{width:100%;border-collapse:collapse}td,th{padding:9px;text-align:left;border-bottom:1px solid #e2e5dd}code,pre{font-family:monospace}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f0;padding:12px}img{max-width:100%;image-rendering:pixelated}.pending{color:#8a521b}a{color:#276748}small{color:#5b665b}</style><main><small>2026-10-15 · 읽기 전용 초기 조사</small><h1>어서와! 치비로보!<br>해피리치 대청소!</h1><p>일본판 B62J · Rev 0 · 64MiB. 원본 롬 변경 및 시험 롬 빌드 없음.</p><div class="stats">'''
 for n,t in [('3,934','이름이 있는 파일'),('17','대사 BMG'),('7,208','글자 포함 항목'),('5','폰트 NFTR')]:page+=f'<div class="stat"><b>{n}</b>{t}</div>'
 page+='''</div><section class="card"><h2>확인한 내용</h2><ul><li>텍스트7,659항목 중 글자가 있는 항목7,208개. 중복·개발용 문구도 포함하므로 최종 번역량은 아직 확정하지 않았습니다.</li><li>Shift-JIS 해독 오류0. 32종의 제어코드 바이트 패턴을 보존했습니다. 코드별 의미는 아직 미확인입니다.</li><li>BMG17개 분해·재인코딩·재저장 후 원본과 바이트 일치. 공백1바이트를 추가한 별도 BMG의 재읽기도 성공했습니다.</li><li>일반 폰트4종은 각각1,015글자. 대사에서 나온 인쇄 가능한 문자를 모두 포함하며 한글은 없습니다.</li><li>ARM9과 오버레이71개 압축 해제 성공. 파일 이름이 없는 FAT71항목은 이 오버레이들과 대응합니다.</li></ul><p class="pending">파일 단위 검증 결과입니다. ROM 재삽입·부팅·한글 출력·팔레트 변환·실행 중 자원 연결은 아직 검증하지 않았습니다.</p></section><section class="card"><h2>대사 파일</h2><table><tr><th>파일</th><th>전체 항목</th><th>글자 포함</th><th>제어코드 포함</th></tr>'''
 for r in a['bmg']:page+=f'<tr><td>{r["file"]}</td><td>{r["entry_count"]}</td><td>{r["nonempty_plain_entries"]}</td><td>{r["entries_with_controls"]}</td></tr>'
 page+='</table><p>공백·개행, %s·%d 변수, 제어코드는 번역 작업에서도 보존해야 합니다.</p></section><section class="card"><h2>폰트 구조</h2><table><tr><th>파일</th><th>셀 크기</th><th>글자 수</th><th>비트 깊이</th></tr>'
 for r in a['fonts']:page+=f'<tr><td>{r["file"]}</td><td>{r["cell_width"]}×{r["cell_height"]}</td><td>{r["glyph_count"]}</td><td>{r["bits_per_pixel"]}bpp</td></tr>'
 page+='</table><p>Font_LoadInfo는23×23, 11글자의 별도 폰트입니다. 일반 대사 폰트와 범위가 다릅니다.</p><p>ARM9에서 대사17개와 large·normal·small 폰트3개의 파일명 문자열을 확인했습니다. 문자열 존재만으로 실제 화면 연결을 확정하지 않았습니다. LoadInfo·smallsmall의 로드 경로는 후속 확인 대상입니다.</p>'
 for r in a['fonts']:
  if r['glyph_count']>11:page+=f'<details><summary>{r["file"]} 추출 글자 샘플</summary><img src="{Path(r["sample_png"]).name}"><p>글자 아래 숫자는 해당 폰트의 글리프 번호입니다.</p></details>'
 page+='</section><section class="card"><h2>그래픽 조사 출발점</h2><p>2D 자원: NCER176개·NCGR305개·NCLR305개·NSCR99개·NANR176개. 모델 NSBMD1,082개와 별도 텍스처 파일도 있습니다. 이 숫자는 파일 수이며 일본어 그림이나 번역 대상의 수가 아닙니다.</p><p>파일 목록에서 title, menu, text3D 등의 이름을 확인할 수 있으나, 그림을 렌더링하여 글자 포함 여부를 분류하는 작업은 아직 하지 않았습니다.</p></section><section class="card"><h2>추출 예시</h2><p>원문 그대로입니다. 꺾쇠 안16진수는 보존한 제어코드입니다.</p>'
 for r in [r for r in entries if r['file']=='MsgResSys.bmg' and 20<=r['index']<=28]:page+=f'<details><summary>{r["file"]} #{r["index"]}</summary><pre>{html.escape(r["text"])}</pre></details>'
 page+='''</section><section class="card"><h2>다음 확인</h2><ol><li>폰트 글자 교체·매핑 확장 방식과 각 폰트 사용 화면 조사.</li><li>줄바꿈·창 폭·변수·제어코드 의미 조사.</li><li>소량 한글 출력 시험 설계. 시험 롬 빌드는 별도 지시 후 진행.</li><li>2D 및3D 텍스트 그림 추출·분류.</li></ol><p>한글은 기본 Shift-JIS에 없으므로 텍스트 인코딩만 바꿔 넣을 수 없습니다. 이 롬의 문자 코드와 폰트 매핑을 함께 검증해야 합니다.</p></section><section class="card"><h2>기록</h2>'''
 for file,label in [('filesystem_inventory.json','파일 목록'),('text_font_analysis.json','텍스트·폰트 분석'),('code_resources.json','코드 압축·리소스 문자열'),('bmg_repack_checks.json','BMG 재저장 검증'),('originals.json','원본 해시')]:page+=f'<p><a href="../../metadata/{file}">{label}</a></p>'
 page+='</section></main></html>';(out/'index.html').write_text(page,encoding='utf-8')
 doc='''# 초기 파일·텍스트·폰트 조사

2026-10-15. 대상 일본판 B62J Rev 0, 원본 SHA-256은 metadata/originals.json 기준.

## 확인 결과

- FAT4,005개: 이름이 있는 파일3,934개와 이름 없는 오버레이71개. 코드 오버레이와 FAT 파일 번호 대응 확인.
- BMG17개, 전체7,659항목, 글자 포함7,208항목. 빈 항목·개발용·중복을 포함하므로 최종 번역 범위가 아니다.
- Shift-JIS 해독 오류0. 고유 문자971개(개행 등 포함), 제어코드32종의 정확한 바이트 패턴 보존. 의미 분석은 별도다.
- 직접 작성한 파서에서 문자열 재인코딩·제어코드 복원으로 동일 바이트 확인. 별도로 설치된 ndspy를 이용한 재저장에서도17개 파일 모두 바이트 동일.
- MsgResSys #20에 ASCII 공백1바이트 추가한 별도 BMG 저장 및 재읽기 성공. 다른 항목 바이트 동일. ROM에 삽입하지 않았다.
- NFTR5개. large15×15, normal11×11, small9×9, smallsmall7×7은 각1,015글자·1bpp. LoadInfo23×23은11글자·1bpp. 일반4종에 본문 인쇄문자 누락0, 한글 매핑0.
- 폰트 비트맵을 직접 디코드하여 샘플 PNG로 확인했다. 글자 폭·매핑 블록은 존재하지만 한글 교체·확장은 미실험이다.
- ARM9은822,212→1,477,528바이트로 압축 해제. 오버레이71개 모두 압축되어 있고 해제 크기가 테이블의 RAM 크기와 일치한다.
- ARM9에서 대사17개 및 폰트3개의 정확한 파일명 문자열20곳을 확인. 이는 실행 추적 또는 함수 호출 참조 증명이 아니다. LoadInfo·smallsmall 로드 경로는 미확인이다.
- 2D 파일 NCER176·NCGR305·NCLR305·NSCR99·NANR176, 모델 NSBMD1,082. 일본어 이미지 수는 아직 분류하지 않았다.

## 검증 한계 및 다음 작업

일반 BMG/NFTR 파일 시작에서 표준 매직을 직접 확인했다. 이를 전체 내부 자원에 압축이 없다는 뜻으로 확대하지 않는다. ARM9과 오버레이는 압축되어 있다.

원본 해시는 재확인했다. ROM 재빌드·주입·부팅·한글 출력·폰트 확장·창 폭·그래픽 인코딩은 미검증이다. 소량 문자 교체 방식을 설계하고 각 폰트 로드 경로를 조사한 뒤, 별도 빌드 지시를 받아 출력 시험을 진행해야 한다. 기존 작품의 폰트·주소·번역·승인은 사용하지 않았다.

검토판: work/initial-analysis/index.html
'''
 (ROOT/'docs/initial-analysis.md').write_text(doc,encoding='utf-8')
 p=ROOT/'project.json';d=json.loads(p.read_text(encoding='utf-8'));d['status']='initial_structure_analysis_complete';d['checks'].update({'filesystem':'metadata/filesystem_inventory.json','text_fonts':'metadata/text_font_analysis.json','code_resources':'metadata/code_resources.json','bmg_repack':'metadata/bmg_repack_checks.json','review':'work/initial-analysis/index.html','report':'docs/initial-analysis.md','hangul_output_verified':False,'font_expansion_verified':False,'rom_rebuild_verified':False});d['next_work']='폰트 매핑·로드 경로와 제어코드·창 폭 추가 조사, 소량 한글 출력 시험 설계. 빌드 지시는 아직 없음.';p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'docs/status.md').write_text('초기 구조 조사를 마쳤다. 자세한 결과와 미확인 항목은 initial-analysis.md 및 project.json에 기록했다. 원본 미변경, 시험 롬 빌드 미진행.\n',encoding='utf-8')
 (ROOT/'.gitignore').write_text('*.nds\n*.sav\nwork/\nbackups/\n__pycache__/\nmetadata/text_entries.json\n',encoding='utf-8')
 (ROOT/'metadata/tool_versions.json').write_text(json.dumps({n:importlib.metadata.version(n) for n in ['ndspy','numpy','Pillow']},indent=2)+'\n',encoding='utf-8')
 for r in a['fonts']:assert (ROOT/r['sample_png']).exists()
 expected=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]['sha256'];assert hashlib.sha256(next(ROOT.glob('*.nds')).read_bytes()).hexdigest()==expected
 print('Review and report saved. Font preview links and unchanged original ROM hash verified.')
if __name__=='__main__':main()
