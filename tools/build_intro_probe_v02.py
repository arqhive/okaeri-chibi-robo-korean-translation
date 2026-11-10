"""Build an opening-sequence probe while retaining every original control token."""
from pathlib import Path
import hashlib
import html
import json
import shutil
from ndspy.bmg import BMG
from prepare_hangul_probe import ROOT, SPECS, expand, parsefont
from render_probe_review import render
from build_hangul_probe import build

OUT = ROOT/'work/output-probe'
RES = OUT/'v02-resources'
# Each list replaces only string parts, leaving all escape objects in place.
CHANGES = {
    'MsgResFamily.bmg': {2: ['이제야 왔구나?'], 3: ['꼬마야\n한참 기다렸어!']},
    'MsgResSys.bmg': {
        720: ['게임 시작을 준비하고 있습니다\n전원을 끄거나\nDS 카드를 만지지 마세요'],
        722: ['데이터를 복사했습니다']
    },
    'MsgResTonpy.bmg': {
        439: ['치비로보 씨!\n일어나세요!'],
        440: ['시간이에요!'],
        441: ['자', '...', '\n드디어 오늘부터네요!'],
        442: ['저기', '...', '듣고 계세요?'],
        443: ['제 소개가 늦었네요!'],
        444: ['저는\n최신형 매니저 로봇', '...'],
        445: ['톤피', '입니다!!'],
        446: ['치비로보 씨도 최신형이에요!'],
        447: ['우리를\n사 주신 분들은'],
        448: ['제니 씨 가족이라고\n해요'],
        449: ['도대체\n어떤 분들일까요!?'],
        450: ['그럼\n이제 둘이서', '...', '아니, 두 대가'],
        451: ['제니 씨 가족을\n행복하게 해 드리도록']
    }
}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def controls(message, encoding):
    return [p.save(encoding) for p in message.stringParts if not isinstance(p, str)]


def main(revision='v02'):
    global RES
    assert revision in ('v02','v03')
    RES = OUT/f'{revision}-resources'
    RES.mkdir(exist_ok=True)
    prior = json.loads((ROOT/'metadata/hangul_probe_preparation.json').read_text(encoding='utf-8'))
    codes = {x['hangul']:int(x['code_hex'],16) for x in prior['mapping']}
    used = set(codes.values())
    for name in SPECS:
        used.update(parsefont((ROOT/'work/extracted'/name).read_bytes())[1])
    available = []
    for code in range(0x889F, 0x9873):
        if code in used:
            continue
        try:
            code.to_bytes(2, 'big').decode('shift_jis')
        except UnicodeDecodeError:
            continue
        available.append(code)
    for messages in CHANGES.values():
        for strings in messages.values():
            for ch in ''.join(strings):
                if '\uac00' <= ch <= '\ud7a3' and ch not in codes:
                    codes[ch] = available.pop(0)
    replacements = {}
    font_checks = []
    for name, spec in SPECS.items():
        raw = (ROOT/'work/extracted'/name).read_bytes()
        replacements[name], _, rec = expand(raw, codes, spec)
        rec.update(file=name, sha256=digest(replacements[name]))
        font_checks.append(rec)
        (RES/name).write_bytes(replacements[name])
    # Exercise original game code, not just a union of CMAP tables.
    from check_game_font_lookup import GameFontLookup
    game_checks=[]
    for name in SPECS:
        data=replacements[name]
        original=(ROOT/'work/extracted'/name).read_bytes()
        oldblocks,oldmap,oldci,oldwi,oldcount,oldcell=parsefont(original)
        blocks,expected,ci,wi,count,cell=parsefont(data)
        engine=GameFontLookup(data)
        for code,glyph in expected.items():
            assert engine.lookup(code)==glyph,(name,hex(code),glyph)
        for glyph in range(count):
            assert engine.widths(glyph)==data[wi+16+glyph*3:wi+19+glyph*3],(name,glyph)
        assert all(expected[code]==glyph for code,glyph in oldmap.items())
        game_checks.append({'font':name,'original_codes_checked':len(oldmap),'all_codes_checked':len(expected),
                            'new_hangul_checked':len(codes),'width_records_checked':count,'all_passed':True})
    message_checks = []
    def proxy(text):
        return ''.join(codes[ch].to_bytes(2,'big').decode('shift_jis') if ch in codes else ch for ch in text)
    for name, changes in CHANGES.items():
        raw = (ROOT/'work/extracted'/name).read_bytes()
        original = BMG(raw)
        obj = BMG(raw)
        for idx, strings in changes.items():
            message = obj.messages[idx]
            assert len(strings) == sum(isinstance(x,str) for x in message.stringParts), (name,idx)
            it = iter(strings)
            message.stringParts = [proxy(next(it)) if isinstance(x,str) else x for x in message.stringParts]
        new = obj.save()
        (RES/name).write_bytes(new)
        replacements[name] = new
        reread = BMG(new)
        assert len(original.messages) == len(reread.messages)
        for idx, (before, after) in enumerate(zip(original.messages,reread.messages)):
            if idx not in changes:
                assert before.save(obj.encoding) == after.save(obj.encoding), (name,idx)
            else:
                assert after.save(obj.encoding) == obj.messages[idx].save(obj.encoding)
                assert controls(before,obj.encoding) == controls(after,obj.encoding)
                assert [p for p in after.stringParts if isinstance(p,str)] == [proxy(s) for s in changes[idx]]
                original_text = ''.join(p for p in before.stringParts if isinstance(p,str))
                korean = ''.join(changes[idx])
                widths = []
                for font in SPECS:
                    img, w = render(replacements[font],korean,codes)
                    _, oldw = render((ROOT/'work/extracted'/font).read_bytes(),original_text,{})
                    stem = f'{Path(font).stem}-{Path(name).stem}-{idx}'
                    img.save(RES/(stem+'.png'))
                    widths.append({'font':font,'original':oldw,'korean':w})
                message_checks.append({'file':name,'index':idx,'original':original_text,'korean':korean,
                                       'control_bytes_preserved':True,'controls_hex':[x.hex() for x in controls(before,obj.encoding)],'widths':widths})
    original_info = json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
    original_path = ROOT/original_info['file']
    source = original_path.read_bytes()
    assert digest(source) == original_info['sha256']
    built, records = build(source,replacements)
    target = OUT/f'ChibiRobo_B62J_KO_probe_{revision}.nds'
    if target.exists():
        assert target.read_bytes() == built, 'Existing v02 differs; use a new revision'
    else:
        target.write_bytes(built)
    assert target.read_bytes() == built
    desktop = Path.home()/'Desktop'/target.name
    if desktop.exists():
        assert desktop.read_bytes() == built, 'Desktop v02 differs; do not overwrite'
    else:
        shutil.copy2(target, desktop)
    assert digest(desktop.read_bytes()) == digest(built)
    assert digest(original_path.read_bytes()) == original_info['sha256']
    report = {'revision':revision,'source_sha256':original_info['sha256'],'output':str(target.relative_to(ROOT)),
              'desktop_copy':str(desktop),'sha256':digest(built),'size_bytes':len(built),
              'glyphs_added_per_font':len(codes),'fonts':font_checks,'messages':message_checks,
              'mapping':[{'hangul':ch,'code_hex':f'{code:04X}','glyph_id':1015+i} for i,(ch,code) in enumerate(codes.items())],
              'replacements':records,'non_target_files_preserved':4005-len(records),
              'rom_readback_verified':True,'header_crc16_verified':True,'original_rom_unchanged':True,
              'control_tokens_preserved':True,'unmodified_messages_preserved':True,
              'desktop_copy_hash_verified':True,'runtime_verified':False,
              'entrypoint_basis':'Content: MsgResSys 720 initial game preparation; MsgResTonpy 439-451 wake-up and self-introduction. Runtime order not observed.',
              'translation_status':'Provisional output probe, not approved glossary or final translation'}
    report['original_game_font_routine_checks']=game_checks
    report['font_mapping_method']='Merge sorted code/glyph pairs into original full-range CMAP; no shadowed extra CMAP'
    (ROOT/f'metadata/probe_build_{revision}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    launch='@echo off\r\ncd /d "%~dp0runtime"\r\nstart "" "%~dp0runtime\\melonDS.exe" "%~dp0ChibiRobo_B62J_KO_probe_v02.nds"\r\n'
    launch=launch.replace('v02',revision)
    (OUT/f'Run_Hangul_Probe_{revision}.cmd').write_bytes(launch.encode('ascii'))
    (OUT/'Run_Hangul_Probe.cmd').write_bytes(launch.encode('ascii'))
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>극초반 한글 시험 v02</title><style>body{font:17px/1.8 system-ui;background:#f2f3eb;color:#253329;margin:0}main{max-width:1050px;margin:auto;padding:32px}section{background:white;border-radius:12px;padding:24px;margin:24px 0}a{color:#276344}img{image-rendering:pixelated;max-width:100%}.row{display:flex;gap:30px;flex-wrap:wrap}pre{white-space:pre-wrap}.pending{color:#895213}</style><main><small>어서와! 치비로보! 해피리치 대청소! · B62J</small><h1>극초반 한글 시험 v02</h1><section><h2>이번에는 여기서 확인하세요</h2><p><b>바탕화면의 ChibiRobo_B62J_KO_probe_v02.nds</b>를 melonDS에서 열어 주세요. v01과 파일명이 다릅니다.</p><ol><li>새 게임으로 시작합니다.</li><li>시작 준비 안내에서 <b>“게임 시작을 준비하고 있습니다”</b>를 확인합니다. 이 안내는 짧게 지나갈 수 있습니다.</li><li>치비로보를 깨우는 도입부에서 <b>“치비로보 씨! 일어나세요!”</b>, <b>“시간이에요!”</b>를 확인합니다. 이어지는 자기소개까지 13개 대사를 바꿨습니다.</li></ol><p>기존 v01의 가족회의 문구는 초반 확인용으로 부적절했습니다. v02는 새 게임 준비 안내와 도입부를 대상으로 합니다. 타이틀 로고나 그림으로 된 버튼은 이번 시험 대상이 아닙니다.</p><p><a href="Run_Hangul_Probe_v02.cmd">별도 melonDS 환경 실행</a> · <a href="ChibiRobo_B62J_KO_probe_v02.nds">v02 ROM</a></p></section><section><h2>바뀐 문구 미리보기</h2><p class="pending">아래는 파일에서 그린 예상 모습입니다. 게임 내 캡처가 아닙니다.</p>'''
    from PIL import Image
    for r in message_checks:
        if (r['file'],r['index']) not in [('MsgResSys.bmg',720),('MsgResTonpy.bmg',439),('MsgResTonpy.bmg',440)]:
            continue
        name=f'Font_normal-{Path(r["file"]).stem}-{r["index"]}.png'
        with Image.open(RES/name) as im:
            w,h=im.size
        page+=f'<h3>{html.escape(r["korean"].splitlines()[0])}</h3><div class="row"><div>원문<pre>{html.escape(r["original"])}</pre></div><div>1배<br><img src="v02-resources/{name}" width="{w}" height="{h}"></div><div>3배<br><img src="v02-resources/{name}" width="{w*3}" height="{h*3}"></div></div>'
    page+='</section><section><h2>도입부 대조표</h2>'
    for r in message_checks:
        if r['file']!='MsgResTonpy.bmg':continue
        page+=f'<details><summary>#{r["index"]} · {html.escape(r["korean"].replace(chr(10)," / "))}</summary><pre>{html.escape(r["original"])}</pre></details>'
    page+=f'''</section><section><h2>검증</h2><p>한글 {len(codes)}자를 일반 폰트 4종에 추가. 총 {len(message_checks)}개 시험 문구, 자원 {len(records)}개 교체. 나머지 파일 {4005-len(records):,}개 및 실행 코드 보존. 대사 제어코드·비대상 메시지 보존, ROM 재읽기·체크섬·바탕화면 복사 해시 검사 통과.</p><p class="pending">원문 내용으로 새 게임 준비와 도입부 문구를 식별했습니다. 실제 등장 순서·부팅·한글 표시는 아직 화면으로 검증하지 못했습니다. 시험 번역이며 용어집 확정본이 아닙니다.</p><p><a href="../../metadata/probe_build_v02.json">v02 검증 기록</a></p></section></main></html>'''
    page=page.replace('v02',revision)
    if revision=='v03':
        page=page.replace('<section><h2>이번에는', '<section><h2>v03 수정 내용</h2><p>v02에서는 기존 전체 범위 문자표가 새 한글 표를 가려 한글 94자 모두 검색에 실패했습니다. 기존 문자표에 한글을 합쳤습니다. 게임의 실제 폰트 검색 코드를 별도로 실행해, 폰트 4종의 기존 문자·새 한글·폭 조회가 모두 일치함을 확인했습니다.</p><p>이 검사는 전체 게임 부팅 검증과 다릅니다. 사용자 첨부의 검은 화면까지 같은 원인인지는 아직 확인하지 못했습니다.</p></section><section><h2>이번에는')
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print('Built',target.name,'and copied to Desktop')
    print('Glyphs:',len(codes),'Messages:',len(message_checks),'Modified files:',len(records))
    for r in message_checks:
        if r['file']=='MsgResTonpy.bmg' or r['index']==720:
            widths=next(w for w in r['widths'] if w['font']=='Font_normal.NFTR')
            print(r['file'],r['index'],widths['original'],'->',widths['korean'])


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--revision',choices=['v02','v03'],default='v02')
    main(parser.parse_args().revision)
