from pathlib import Path
import json,struct,hashlib,html
import numpy as np
from PIL import Image
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
from prepare_hangul_probe import ROOT,OUT,SPECS,TEXTS,parsefont
from analyze_text_fonts import u16,u32

def glyph(b,code):
 _,mp,ci,wi,count,cell=parsefont(b);w,h=b[ci+8:ci+10];g=mp[code];bits=np.unpackbits(np.frombuffer(b[ci+16+g*cell:ci+16+(g+1)*cell],dtype=np.uint8))[:w*h].reshape(h,w);left,cw,advance=struct.unpack_from('<bBB',b,wi+16+g*3);return Image.fromarray((bits*255).astype('uint8')),left,advance

def render(b,text,codes):
 _,mp,ci,wi,count,cell=parsefont(b);w,h=b[ci+8:ci+10];lines=text.splitlines();runs=[];widths=[]
 for line in lines:
  run=[];x=0
  for c in line:
   code=codes[c] if c in codes else int.from_bytes(c.encode('shift_jis'),'big');im,left,adv=glyph(b,code);run.append((x+left,im));x+=adv
  widths.append(x);runs.append(run)
 canvas=Image.new('RGBA',(max(1,max(widths))+2,(h+3)*len(lines)),(255,255,255,255))
 for i,run in enumerate(runs):
  for x,im in run:canvas.paste((0,0,0,255),(x+1,i*(h+3)),im)
 return canvas,widths

def main():
 report=json.loads((ROOT/'metadata/hangul_probe_preparation.json').read_text(encoding='utf-8'));codes={r['hangul']:int(r['code_hex'],16) for r in report['mapping']};rawtext=json.loads((ROOT/'metadata/text_entries.json').read_text(encoding='utf-8'));lookup={(r['file'],r['index']):r['text'] for r in rawtext}
 checks=[]
 for rec in report['fonts']:
  name=rec['file'];b=(OUT/name).read_bytes();bs,mp,ci,wi,count,cell=parsefont(b);starts={o+8:(k,o,n) for k,o,n in bs};fi=next(o for k,o,n in bs if k=='FNIF');visited=[];ptr=u32(b,fi+24)
  assert starts[u32(b,fi+16)][0]=='PLGC' and starts[u32(b,fi+20)][0]=='HDWC'
  while ptr:
   assert ptr not in visited;visited.append(ptr);k,o,n=starts[ptr];assert k=='PAMC';ptr=u32(b,o+16)
  assert len(visited)==sum(k=='PAMC' for k,o,n in bs)
  for file,idx,t in TEXTS:
   original=lookup[(file,idx)];orig,ow=render((ROOT/'work/extracted'/name).read_bytes(),original,{});new,nw=render(b,t,codes);stem=f'{Path(name).stem}-{Path(file).stem}-{idx}';orig.save(OUT/(stem+'-original.png'));new.save(OUT/(stem+'-korean.png'));checks.append({'font':name,'file':file,'index':idx,'original_text':original,'korean_text':t,'original_widths':ow,'korean_widths':nw,'image_stem':stem})
  rec['all_cmap_blocks_reachable_from_finf']=True
  rec['font_source_sha256']=hashlib.sha256((Path.home()/'AppData/Local/Microsoft/Windows/Fonts'/(rec['font_family']+'.ttf')).read_bytes()).hexdigest()
 report['render_checks']=checks
 arm=(ROOT/'work/code/arm9.bin').read_bytes();base=0x02000000;table=0x2148c2c;entries=[]
 for i in range(5):
  addr=u32(arm,table-base+4*i);off=addr-base;end=arm.index(0,off);name=arm[off:end].decode('ascii');entries.append({'index':i,'name_in_arm9':name,'pointer_address':table+4*i,'string_address':addr,'matching_file':next(p.name for p in (ROOT/'work/extracted').glob('*.NFTR') if p.name.lower()==name.lower()),'loaded_by_observed_init_loop':1<=i<5})
 cs=Cs(CS_ARCH_ARM,CS_MODE_ARM);instructions=[{'address':hex(i.address),'mnemonic':i.mnemonic,'operands':i.op_str} for i in cs.disasm(arm[0x1e4fc:0x1e54c],0x201e4fc)]
 report['font_loader_static']={'table_address':table,'entries':entries,'init_function':0x201e4fc,'loop_first_index':1,'loop_end_exclusive':5,'resource_call':0x1ff80c0,'post_load_call':0x210ee14,'instructions':instructions,'runtime_verified':False,'note':'Index0 smallsmall is in table but not loaded by this specific loop; further paths not traced.'}
 report['font_expansion_static_verified']=True;report['actual_window_widths_verified']=False
 (ROOT/'metadata/hangul_probe_preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>한글 출력 시험 준비</title><style>body{font:16px/1.7 system-ui;background:#f2f3eb;color:#26352b;margin:0}main{max-width:1150px;margin:auto;padding:32px}section{background:white;border:1px solid #d9dfd2;border-radius:12px;padding:24px;margin:24px 0}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}.row{display:flex;gap:24px;flex-wrap:wrap}img{image-rendering:pixelated;max-width:100%}pre{white-space:pre-wrap}.pending{color:#895213}a{color:#286642}</style><main><small>2026-10-15 · 원본 B62J Rev0</small><h1>어서와! 치비로보!<br>소량 한글 출력 시험 준비</h1><p>새 한글22글자를 일반 폰트4종에 추가했습니다. 기존 일본어1,015글자와 폭·매핑을 보존했습니다.</p><p class="pending">아래 그림은 수정 NFTR을 다시 읽어 만든 글자 미리보기입니다. 게임 화면 캡처가 아닙니다. 시험 롬은 아직 만들지 않았습니다.</p><section><h2>파일 단위 확인</h2><ul><li>각 폰트1,015→1,037글자. 기존 글리프 바이트·폭·문자 매핑 동일.</li><li>CGLP·CWDH·CMAP 확장 후 FINF 및 다음 블록 포인터 연결 확인.</li><li>3개 문구의 재인코딩·BMG 재읽기 통과. 다른 메시지는 바이트 동일.</li><li>문구는 임시 출력 시험 번역이며, 정식 용어·말투 확정본이 아닙니다.</li></ul><table><tr><th>폰트</th><th>셀</th><th>시험 글꼴</th><th>파일 크기</th></tr>'''
 for r in report['fonts']:page+=f'<tr><td>{r["file"]}</td><td>{r["cell"][0]}×{r["cell"][1]}</td><td>{r["font_family"]} {r["font_px"]}px</td><td>{r["old_size"]:,} → {r["new_size"]:,}</td></tr>'
 page+='</table><p>이 롬의 셀 크기에 맞춰 시험 글꼴을 선택했습니다. 글리프 자체를 확대·축소하지 않았습니다. LoadInfo23×23 폰트는 수정하지 않았습니다.</p></section><section><h2>문자 코드 방식</h2><p>원본 폰트에 매핑되지 않은 유효한 Shift-JIS 코드22개를 시험용 한글에 배정했습니다. 기존 일본어 코드는 그대로입니다. 이 매핑은 게임 전용이며 BMG를 일반 일본어 뷰어로 보면 한자로 표시됩니다.</p><p class="pending">전체 번역에 필요한 글자 수·메모리 여유·글리프1,024개 이상 처리·실제 렌더러 동작은 게임 실행으로 확인해야 합니다.</p></section><section><h2>폰트 로드 경로</h2><p>ARM9의0x02148C2C 폰트 목록과0x0201E4FC 초기화 루프를 확인했습니다. 해당 루프는 small·normal·large·loadInfo를 읽습니다. smallsmall은 목록에는 있지만 이 루프 범위 밖입니다.</p><p>LoadInfo / loadInfo, smallsmall / smallSmall 대소문자 차이로 처음 검색에서 놓친 이름도 연결했습니다. 실제 화면별 폰트 선택은 아직 미확인입니다.</p></section><section><h2>시험 문구와 확인 경로</h2><ul><li>MsgResFamily #2·#3: 가족 소개 대사로 보이는 첫 부분. 등장 순서는 실제 플레이에서 확인해야 합니다.</li><li>MsgResSys #722: 데이터 복사 완료 문구. 추후 시험은 별도 테스트 저장 파일로 진행하고 기존 저장 파일은 보호해야 합니다.</li></ul><p>이번에는 BMG와 폰트 파일만 준비했으며 저장 파일 조작은 하지 않았습니다.</p></section>'
 for r in checks:
  if r['font']!='Font_normal.NFTR':continue
  page+=f'<section><h2>{r["file"]} #{r["index"]}</h2><div class="row"><div>일본어<pre>{html.escape(r["original_text"])}</pre></div><div>시험 한국어<pre>{html.escape(r["korean_text"])}</pre></div></div>'
  for name in SPECS:
   rr=next(q for q in checks if q['font']==name and q['file']==r['file'] and q['index']==r['index']);page+=f'<details {"open" if name=="Font_normal.NFTR" else ""}><summary>{name} · 한국어 줄 폭 {rr["korean_widths"]}px</summary>'
   for scale in (1,3):
    page+=f'<p>{scale}배</p><div class="row">'
    for suffix,title in [('original','원문'),('korean','시험 한글')]:
     filename=rr['image_stem']+'-'+suffix+'.png'
     with Image.open(OUT/filename) as im:w,h=im.size
     page+=f'<div>{title}<br><img src="{filename}" width="{w*scale}" height="{h*scale}"></div>'
    page+='</div>'
   page+='</details>'
  page+='</section>'
 page+='''<section><h2>남은 검증</h2><p>시험 롬 빌드·부팅·한글 출력, 폰트 메모리와 긴 줄 잘림, smallsmall 추가 로드 경로. 원본 ROM 해시는 유지했습니다.</p><p><a href="../../metadata/hangul_probe_preparation.json">매핑·검증·정적 코드 분석 기록</a> · <a href="../initial-analysis/index.html">초기 조사</a></p></section></main>''';(OUT/'index.html').write_text(page,encoding='utf-8')
 print('CMap chains, rebuilt glyphs, message widths and review validated.')
 for r in checks:
  if r['font']=='Font_normal.NFTR':print(r['file'],r['index'],r['original_widths'],'->',r['korean_widths'])
if __name__=='__main__':main()
