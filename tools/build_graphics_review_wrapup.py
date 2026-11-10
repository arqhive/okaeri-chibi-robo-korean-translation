"""Record the end of independent PNG review batches without claiming runtime completion."""
from pathlib import Path
from collections import Counter
import json,html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/review-wrapup';OUT.mkdir(exist_ok=True)
w=json.loads((ROOT/'metadata/graphics_worklist.json').read_text('utf8'));confirmed=[a for r in w['items'] if r['scope']=='confirmed' for a in r['assets']];stages=Counter(a.get('draft_stage','none') for a in confirmed)
assert stages==dict(approved=637,pending_composition=27,unchanged_nontext=2,draft=1,none=2),stages
remaining=[]
for r in w['items']:
 for a in r['assets']:
  if a.get('draft_stage')!='pending_composition':continue
  src='../../graphics-review/'+a['image'];remaining.append(f'<tr><td>{r["id"]}/cell/{a["cell"]}</td><td><img src="{html.escape(src)}" width="{a["width"]*3}" height="{a["height"]*3}" alt="{r["id"]} cell {a["cell"]}"></td><td>{html.escape(" ".join(a["draft_notes"]))}</td></tr>')
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>그림 검토 현황</title><style>body{background:#edf1e7;color:#172016;font:16px/1.65 system-ui;margin:0}main{max-width:1080px;padding:32px;margin:auto}article,details{background:white;padding:24px;border-radius:12px;margin:20px 0}h1{margin-bottom:8px}h2{font-size:21px}.count{font-size:44px;font-weight:700;color:#285d39}a{color:#285d39}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #dfe5da;text-align:left;padding:12px}img{image-rendering:pixelated;display:block;background:#ddd}summary{cursor:pointer;font-weight:bold}</style><main><h1>새 문구 PNG 검토 묶음 완료</h1><p>마지막 메뉴·홈쇼핑 6개까지 검토 승인으로 기록했습니다.</p><article><div class="count">637개 승인</div><p>원본 유지 및 확인 대기 항목은 승인 수에 포함하지 않았습니다.</p><a href="../final-ui-v1/index.html?revision=ticker-imagegen-v4">마지막 묶음 다시 보기</a> · <a href="../../graphics-review/dashboard.html">전체 그림 현황판</a></article><article><h2>남은 확인</h2><table><tr><th>항목</th><th>수량</th><th>상태</th></tr><tr><td>UI 조각</td><td>27개</td><td>표시 조합·타일 연결 확인. 별도 문구로 임의 번역하지 않음.</td></tr><tr><td>G0027/cell/10 · 없음</td><td>1개</td><td>사용자 지정대로 게임에서 확인 후 수정.</td></tr><tr><td>글씨 없는 그림</td><td>2개</td><td>원본 유지.</td></tr><tr><td>TV 광고 텍스처</td><td>2개</td><td>지정된 작업방식에 따라 원본 유지.</td></tr></table><p>판독·연결 미확인 카테고리 역시 기존 원본 유지 결정을 따릅니다.</p></article><article><h2>다음 작업 단계</h2><p>UI 조각의 실제 표시 조합과 공유 타일을 확인한 뒤 그래픽 반영 및 게임 표시 검증이 필요합니다. PNG 승인만으로 그래픽 ROM 반영이나 게임 내 표시 확인이 끝난 것은 아닙니다.</p></article><details><summary>연결 확인이 남은 UI 조각 27개</summary><table><tr><th>자원</th><th>원본 조각</th><th>확인 사항</th></tr>'''+''.join(remaining)+'</table></details></main></html>'
(OUT/'index.html').write_text(page,'utf8')
report=dict(confirmed_asset_references=len(confirmed),stages=dict(stages),approved_asset_references=637,composition_pending=27,deferred_in_game=1,standalone_new_png_batches_remaining=0,rom_inserted=False,runtime_verified=False)
(ROOT/'metadata/graphics_png_review_wrapup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(ROOT/'docs/graphics-png-review-wrapup.md').write_text('''# PNG 검토 묶음 정리

사용자 ㅇㅋ다ㅏ음묶음 요청으로 final-ui-v1 ticker-imagegen-v4의 6개를 승인 기록했다. 승인 자원 참조 합계 637개. 독립 문구의 새 PNG 묶음은 남지 않았다.

확인된 669개 자원 참조의 합계는 승인 637 + 조합 대기 27 + 게임 확인 보류 1 + 비문자 원본 유지 2 + TV 원본 유지 2이다. 27개 조각을 승인이나 작업 완료로 바꾸지 않았다. G0027/10 없음은 게임 확인 보류를 그대로 유지한다. 이 합계는 고유 PNG 파일 수나 별도 그림 수와 다를 수 있다.

원본 유지로 지정된 판독·연결 미확인 카테고리는 새 번역 묶음에 포함하지 않았다. 그래픽 ROM 삽입과 게임 검증은 미완료다.
''','utf8')
print(report)
