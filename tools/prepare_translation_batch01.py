"""Create a reviewable, control-preserving first translation batch; no ROM build."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,hashlib,collections
from translation_batch01_data import CHANGES
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/translation-review'
CTRL=re.compile(r'<[0-9a-fA-F]+>')
FMT=re.compile(r'%(?:\d+\$)?[-+# 0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]*[diuoxXfFeEgGcs%]')
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,j):(ROOT/p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def visible(s):return CTRL.sub('',s)
def joined(parts):return ''.join(p['text'] if 'text' in p else '<'+p['control_hex']+'>' for p in parts)
def esc(s):return __import__('html').escape(str(s))
def main():
 OUT.mkdir(parents=True,exist_ok=True);(ROOT/'translations').mkdir(exist_ok=True)
 entries=read('metadata/text_entries.json');terms=read('metadata/terminology_proposals.json');sourcehash=hashlib.sha256((ROOT/'metadata/text_entries.json').read_bytes()).hexdigest()
 adopted=dict(terms,status='adopted_for_translation',approved=True,approval_basis='용어·말투 검토안 제시 후 사용자: 다음')
 for r in adopted['terms']:r['status']='adopted'
 for r in adopted['voice_proposals']:r['status']='adopted_style_proposal';r['speaker_runtime_verified']=False
 save('metadata/terminology_approved.json',adopted)
 # Exact short labels only; never replace substrings inside dialogue.
 termmap={r['source']:r for r in adopted['terms']};changes={f:{i:list(s) for i,s in rows.items()} for f,rows in CHANGES.items()};labelids=set()
 for r in entries:
  if r['file']!='MsgResSys.bmg' or r['index'] in changes['MsgResSys.bmg']:continue
  jp=visible(r['text']);tp=[p['text'] for p in r['parts'] if 'text' in p]
  if jp in termmap and len(tp)==1:
   changes[r['file']][r['index']]=[termmap[jp]['proposed_ko']];labelids.add(r['index'])
 rows=[];batch=[]
 for r in entries:
  key=f'{r["file"]}#{r["index"]}';tp=[p['text'] for p in r['parts'] if 'text' in p];hastext=bool(''.join(tp).strip());segs=changes.get(r['file'],{}).get(r['index'])
  rec={'id':key,'file':r['file'],'index':r['index'],'source':r['text'],'source_parts':r['parts'],'source_sha256':hashlib.sha256(r['text'].encode()).hexdigest(),'status':'pending' if hastext else 'empty_or_control_only','translation':None,'translation_parts':None}
  if segs is not None:
   assert len(tp)==len(segs),(key,tp,segs)
   it=iter(segs);parts=[{'text':next(it)} if 'text' in p else dict(p) for p in r['parts']];ko=joined(parts)
   assert CTRL.findall(r['text'])==CTRL.findall(ko),key
   assert FMT.findall(r['text'])==FMT.findall(ko),key
   assert not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',visible(ko)),key
   section='기본 메뉴·이름' if r['file']=='MsgResSys.bmg' and r['index'] in labelids else '저장·시스템' if r['file']=='MsgResSys.bmg' else '첫 가족회의·청소' if r['file']=='MsgResFamily.bmg' else '새 게임·조작 안내' if r['index']>=439 else '톤피의 기본 안내'
   flags=[]
   if FMT.findall(ko):flags.append('치환 후 조사·문장 폭 확인')
   if len(visible(ko).splitlines())>2:flags.append('3줄 이상: 실제 창 높이 확인')
   if any(len(x)>20 for x in visible(ko).splitlines()):flags.append('긴 줄: 실제 글꼴 폭 확인')
   rec.update(status='draft',translation=ko,translation_parts=parts,batch='batch01',section=section,method='approved_exact_label' if r['file']=='MsgResSys.bmg' and r['index'] in labelids else 'authored_context_translation',review_flags=flags,runtime_verified=False,control_sequence_verified=True,placeholder_sequence_verified=True)
   batch.append(rec)
  rows.append(rec)
 expected={(f,i) for f,rs in changes.items() for i in rs};assert expected=={(r['file'],r['index']) for r in batch}
 stats=dict(collections.Counter(r['status'] for r in rows));assert stats['pending']+stats['draft']==7208
 manifest={'project':terms['project'],'batch':'batch01','scope':'새 게임 소개·조작 안내 / 첫 가족회의와 청소 / 톤피 기본 안내 / 메뉴·아이템·저장 메시지','source_entries_sha256':sourcehash,'counts':stats,'batch_count':len(batch),'by_section':dict(collections.Counter(r['section'] for r in batch)),'authored_count':sum(r['method']=='authored_context_translation' for r in batch),'exact_label_count':len(labelids),'review_flags':dict(collections.Counter(f for r in batch for f in r['review_flags'])),'terminology':'metadata/terminology_approved.json','rom_built':False,'runtime_verified':False,'notes':['모든 제어 바이트 및 printf 치환자의 순서를 유지했다.','일부 항목은 앞뒤 메시지와 이어지는 문장 조각이다. 화자 및 실제 분기 순서는 게임 장면에서 검증해야 한다.','검토판은 일반 글꼴로 표시하는 번역 대조표다. DS 화면 배치나 한글 인코딩·삽입 성공을 뜻하지 않는다.','본문 7208항목 중 첫 묶음만 초안이며 나머지는 pending이다.']}
 save('translations/entries.json',{'schema_version':1,'source_entries_sha256':sourcehash,'entries':rows});save('translations/batch01.json',{'manifest':manifest,'entries':batch});save('metadata/translation_progress.json',manifest)
 # Sections shown in play-friendly order, while preserving source IDs within each.
 order=['새 게임·조작 안내','첫 가족회의·청소','톤피의 기본 안내','기본 메뉴·이름','저장·시스템']
 css='''body{margin:0;background:#eff3ed;color:#22372b;font:16px/1.7 system-ui,sans-serif}main{max-width:1250px;margin:auto;padding:30px}h1{font-size:28px}.panel,article{background:white;padding:22px;margin:16px 0;border-radius:12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}.pair>div{min-width:0}.source{color:#4c5a50}pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0}.badge{display:inline-block;background:#e1ecd9;padding:4px 9px;border-radius:5px;margin:3px}.flag{color:#775417;font-size:13px}small{color:#607066}input,select{font:inherit;padding:9px;border:1px solid #abc0ac;border-radius:6px}input{width:45%}a{color:#166b4c}nav{display:flex;gap:18px;flex-wrap:wrap}details{margin-top:14px}code{font-size:12px;overflow-wrap:anywhere}h3{margin:0 0 10px;font-size:16px}article[hidden]{display:none}@media(max-width:700px){main{padding:12px}.pair{grid-template-columns:1fr;gap:10px}}'''
 doc=['<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>해피리치 대청소 · 본문 번역 01</title><style>'+css+'</style><main><h1>어서와! 치비로보! 해피리치 대청소!<br>본문 번역 · 첫 묶음</h1>',f'<p><span class="badge">초안 {len(batch):,} / 7,208항목</span><span class="badge">미번역 {stats["pending"]:,}항목</span><span class="badge">제어 코드·치환자 보존 확인</span></p><nav><a href="../terminology-review/index.html">채택한 용어·말투</a><a href="../scope-deep/index.html">조사 결과</a><a href="../../translations/batch01.json">첫 묶음 JSON</a><a href="../../metadata/translation_batch01_validation.json">검증 결과</a></nav><div class="panel"><p>새 게임에서 톤피가 깨우는 장면부터 첫 가족회의·청소 안내까지 번역했습니다. 기본 메뉴·아이템명과 저장 메시지도 포함했습니다.</p><p><b>검토용 번역 대조표입니다.</b> 줄바꿈과 치환 후 조사, 실제 게임 창 크기는 삽입 단계에서 확인합니다. 이번 단계에서는 새 ROM을 빌드하지 않았습니다.</p><label>검색 <input id="q" placeholder="한국어·일본어·파일·번호"></label> <select id="section"><option value="">전체 묶음</option>']
 for s in order:doc.append(f'<option>{esc(s)}</option>')
 doc.append('</select><p id="count"></p></div>')
 for s in order:
  doc.append(f'<h2>{esc(s)}</h2>')
  for r in sorted((r for r in batch if r['section']==s),key=lambda r:(r['file'],r['index'])):
   anchor=r['file'].replace('.bmg','')+'-'+str(r['index']);jp=visible(r['source']);ko=visible(r['translation']);nc=len(CTRL.findall(r['source']))
   doc.append(f'<article id="{anchor}" data-section="{esc(s)}"><h3>{esc(r["id"])}</h3><div class="pair"><div class="source"><small>일본어 원문</small><pre lang="ja">{esc(jp)}</pre></div><div><small>한국어 초안</small><pre lang="ko">{esc(ko)}</pre></div></div><small>제어 코드 {nc}개 · 치환자 {len(FMT.findall(r["source"]))}개</small>')
   if r['review_flags']:doc.append('<p class="flag">'+esc(' · '.join(r['review_flags']))+'</p>')
   doc.append(f'<details><summary>제어 코드 포함 대조</summary><div class="pair"><code>{esc(r["source"])}</code><code>{esc(r["translation"])}</code></div></details></article>')
 doc.append('<script>const q=document.querySelector("#q"),s=document.querySelector("#section"),rs=[...document.querySelectorAll("article")];function filter(){let n=0;rs.forEach(r=>{r.hidden=!((!s.value||s.value===r.dataset.section)&&r.textContent.toLowerCase().includes(q.value.toLowerCase()));if(!r.hidden)n++});document.querySelector("#count").textContent=n+" / "+rs.length+"항목 표시"}q.oninput=s.onchange=filter;filter();</script></main></html>');(OUT/'index.html').write_text(''.join(doc),encoding='utf-8')
 # Keep the former proposal page accessible with its adoption status made explicit.
 prior=ROOT/'work/terminology-review/index.html';body=prior.read_text(encoding='utf-8');body=body.replace('검토 초안 · 미승인','본문 번역 기준 · 채택').replace('현재 표기는 이 작품의 원문에서 만든 제안입니다. 용어와 말투를 검토하는 단계로, ROM에는 아직 본문 번역을 넣지 않았습니다.','사용자의 다음 단계 진행 지시에 따라 이 용어·말투안을 본문 번역 기준으로 채택했습니다. 화자 추정 및 실행 확인 보류는 그대로 유지합니다.').replace('../../metadata/terminology_proposals.json','../../metadata/terminology_approved.json');prior.write_text(body,encoding='utf-8')
 p=read('project.json');p['status']='translation_batch01_review_ready';p['decisions']['terminology_approved']=True;p['checks'].update(review='work/translation-review/index.html',report='docs/translation-batch01.md',terminology='metadata/terminology_approved.json',translation_progress='metadata/translation_progress.json');p['next_work']='본문 첫 묶음 검토 후 나머지 항목 번역. 창 폭·화자·치환 후 조사와 ROM 삽입은 별도 검증.';save('project.json',p)
 report=f'# 본문 번역 첫 묶음\n\n용어안은 사용자의 다음 지시로 채택했다. 초안 {len(batch)} / 7208항목, 나머지 {stats["pending"]}항목 대기.\n\n'+ '\n'.join(f'- {k}: {v}항목' for k,v in manifest['by_section'].items())+'\n\n검토판: work/translation-review/index.html\n편집 데이터: translations/entries.json 및 translations/batch01.json\n\n제어 코드·치환자 순서 보존 확인. 원문 수정 없음. 화면 배치·한글 인코딩·실행 검증 및 새 ROM 빌드는 아직 하지 않았다.\n'
 (ROOT/'docs/translation-batch01.md').write_text(report,encoding='utf-8');(ROOT/'docs/status.md').write_text(report,encoding='utf-8')
 print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
