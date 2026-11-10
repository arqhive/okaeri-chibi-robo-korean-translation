"""Publish verified full-text build status without marking runtime checks complete."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]

def read(p):
    return json.loads((ROOT/p).read_text(encoding='utf8'))

def save(p,obj):
    (ROOT/p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.ids=[];self.in_data=False;self.data=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id'in a:self.ids.append(a['id'])
        for k in ('src','href'):
            if k in a:self.links.append(a[k])
        if tag=='script'and a.get('id')=='data':self.in_data=True
    def handle_endtag(self,tag):
        if tag=='script':self.in_data=False
    def handle_data(self,data):
        if self.in_data:self.data+=data

def main():
    r=read('metadata/fulltext_build_v01.json')
    for path in [ROOT/r['output'],Path(r['desktop_copy'])]:
        assert path.stat().st_size==r['size_bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
    doc=f'''# 본문 시험 ROM v01 · 게임 내 검수 대기

바탕화면: `{r['desktop_copy']}`

프로젝트 출력: `{r['output']}`

원본과 같은 64MiB(67,108,864바이트)다. 번역 모델 가중치는 이 빌드에 포함되지 않으며 추가 다운로드도 없다.

## 적용 범위

- 본문 17개 BMG에서 한국어 7,095항목을 삽입했다.
- 영어·기호 113항목과 빈 항목·제어 전용 451항목은 바이트 그대로 보존했다.
- 일반 NFTR 4종에 한글 1,023자를 추가했다. v03의 문자 할당은 유지한다.
- 가운데점 U+00B7은 게임의 기존 U+30FB 글리프로 인코딩했다. 적용한 14항목은 빌드 기록에 남겼고 번역 원고는 변경하지 않았다.
- 원본 ROM의 FF 여유 공간에 21개 자원, 합계 432,528바이트를 추가했다. ROM 전체 크기는 늘지 않았다.

## 통과한 검사

- BMG 직렬화 및 재읽기, 메시지 수·속성·흐름 데이터 보존.
- 제어코드 7,648개와 printf 치환자 347개 보존.
- 기존 글리프·폭·문자 매핑 보존 및 새 한글의 원본 TTF 수록 확인.
- 원래 게임의 문자 조회·폭 조회 함수를 Unicorn에서 실행하여 네 글꼴의 전체 매핑과 폭 레코드 검사.
- 교체 자원 외 3,984개 파일, 실행 코드, 오버레이 표, 배너, 파일명 표 보존.
- ROM 재읽기, 헤더 CRC16, 원본 해시 및 바탕화면 복사본 해시 확인.
- ROM에 넣은 NFTR 바이트로 도입부 4문구를 렌더링해 확대 모양을 확인했다. 게임 캡처는 아니다.

출력 SHA-256: `{r['sha256']}`

## 글자 폭 측정과 한계

7,208항목을 네 글꼴로 측정했다. 일반 글꼴에서 256px 초과 0항목, 원문보다 긴 항목 750개, 동적 치환 포함 284항목이다. 최대 224px는 문자 목록 형태인 MsgResSys #3이다. 문자 목록형 항목의 실제 용도·표시 경로도 실행 검수 대상이다.

이 값은 CWDH의 글자 진행 폭을 더한 선별 자료다. 실제 창 너비, 폰트 전환, 자간, 확대, 페이지 제어, 치환 후 문자열을 재현하지 않았다. 따라서 넘침 없음이나 게임 진행 정상의 증거가 아니다. 번역 원고의 줄바꿈은 빌드 시 변경하지 않았다.

## 아직 적용·검증하지 않은 범위

그림 속 일본어와 실행 코드 직접 문자열 후보 7개는 미적용이다. 특수 LoadInfo 글꼴(공백과 0x8740..0x8749)은 그대로 보존했다. 본문 전체 빌드의 부팅, 폰트 메모리 사용량, 장면별 배치와 게임 진행은 미검증이다. 사용자가 확인한 한글 출력은 이전 v03 시험판에 한정된다.

새 ROM에서 새 게임을 시작해 톤피의 도입부 대사부터 확인한다. 이전 ROM의 세이브스테이트로 이번 빌드의 성공 여부를 판단하지 않는다. 사용자의 기존 세이브 파일은 건드리지 않았다.

## 산출물

- `work/output-fulltext/index.html`: 빌드 안내와 글꼴 미리보기.
- `work/output-fulltext/layout.html`: 긴 줄부터 보는 원문·번역 점검표.
- `metadata/fulltext_build_v01.json`: 적용 파일, 문자 할당, 검증 기록.
- `metadata/fulltext_layout_v01.json`: 글꼴 4종의 전체 측정값.
- `tools/build_full_text.py`: 원본에서 재생성하는 빌드 스크립트.

다음은 새 시험판의 실행 확인 및 그래픽 번역 단계다.
'''
    (ROOT/'docs/fulltext-build-v01.md').write_text(doc,encoding='utf8')
    (ROOT/'docs/status.md').write_text(doc,encoding='utf8')
    p=read('project.json');p['status']='full_text_test_rom_built_runtime_pending'
    p['checks'].update(fulltext_build='metadata/fulltext_build_v01.json',fulltext_layout='metadata/fulltext_layout_v01.json',review='work/output-fulltext/index.html',report='docs/fulltext-build-v01.md',fulltext_runtime_verified=False)
    p['next_work']='본문 전체 시험 ROM의 실행·배치·진행 확인 및 그림 글자 번역 준비'
    save('project.json',p)
    progress=read('metadata/translation_progress.json')
    progress.update(stage=p['status'],rom_built=True,build='metadata/fulltext_build_v01.json',runtime_verified=False)
    progress['notes']=[n for n in progress['notes']if 'ROM 삽입은 다음'not in n]
    progress['notes'].append('본문 시험 ROM fulltext_v01 제작 및 바탕화면 복사 완료. 글꼴 폭 정적 측정은 완료했으며 실제 창 배치·진행은 미검증. 그림 글자와 코드 후보 7개는 아직 미적용.')
    save('metadata/translation_progress.json',progress)
    unresolved=read('metadata/translation_unresolved.json')
    unresolved['runtime_tasks']=['본문 전체 시험판의 부팅·글꼴 메모리 사용·게임 진행 확인','화자·분기·연결 대사 확인','실제 창 폭·글꼴 전환·줄 수·치환 후 조사 확인','문자 목록형 MsgResSys #1~3의 실행 용도 확인','직접 코드 문자열 CP932 한글 처리 경로 검증']
    save('metadata/translation_unresolved.json',unresolved)
    review=ROOT/'work/translation-review/index.html'
    page=review.read_text(encoding='utf8')
    page=page.replace('새 ROM은 아직 만들지 않았습니다.','본문 시험 ROM fulltext_v01을 제작해 바탕화면에 복사했습니다. <a href="../output-fulltext/index.html">시험판과 글자 폭 점검 보기</a>. 실제 게임 내 검수는 아직입니다.')
    review.write_text(page,encoding='utf8')
    validation=[]
    for rel in ['work/output-fulltext/index.html','work/output-fulltext/layout.html','work/translation-review/index.html']:
        path=ROOT/rel;parser=Links();parser.feed(path.read_text(encoding='utf8'))
        assert len(parser.ids)==len(set(parser.ids)),rel
        links=0
        for link in parser.links:
            u=urlsplit(link)
            if u.scheme or not u.path:continue
            assert (path.parent/unquote(u.path)).exists(),(rel,link)
            links+=1
        data=json.loads(parser.data)if parser.data else None
        if data is not None:assert len(data)==7208,rel
        validation.append({'page':rel,'local_links_checked':links,'embedded_rows':len(data)if data else 0})
    save('metadata/fulltext_review_validation_v01.json',{'pages':validation,'static_validation_passed':True,'runtime_verified':False})
    print(json.dumps(validation,ensure_ascii=False))

if __name__=='__main__':main()
