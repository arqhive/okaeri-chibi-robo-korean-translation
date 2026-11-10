"""Prepare an isolated copy of the user's existing emulator, without launching it."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import tomllib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/output-probe'
SOURCE = Path('C:/Users/hgyst/Desktop/melonDS')
RUNTIME = OUT/'runtime'


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for folder in ['saves', 'states', 'cheats']:
        (OUT/folder).mkdir(exist_ok=True)
    hashes = {}
    for name in ['melonDS.exe', 'biosnds7.bin', 'biosnds9.bin', 'dsfirmware.bin']:
        source = SOURCE/name
        dest = RUNTIME/name
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if not dest.exists():
            shutil.copy2(source, dest)
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
        hashes[name] = digest
    q = lambda p: json.dumps(str(p).replace('\\', '/'))
    config = f'''RecentROM = []
LimitFPS = true
TargetFPS = 60.0
PauseLostFocus = false

[Emu]
ConsoleType = 0
DirectBoot = true
ExternalBIOSEnable = true

[DS]
BIOS9Path = {q(RUNTIME/'biosnds9.bin')}
BIOS7Path = {q(RUNTIME/'biosnds7.bin')}
FirmwarePath = {q(RUNTIME/'dsfirmware.bin')}

[Instance0]
SaveFilePath = {q(OUT/'saves')}
SavestatePath = {q(OUT/'states')}
CheatFilePath = {q(OUT/'cheats')}
EnableCheats = false

[Instance0.Keyboard]
Up = 87
Down = 83
Left = 65
Right = 68
A = 74
B = 75
X = 85
Y = 73
L = 81
R = 69
Start = 16777220
Select = 32

[Instance0.Window0]
Enabled = true
ScreenFilter = false
ScreenLayout = 0
ScreenGap = 0

[JIT]
Enable = false
'''
    parsed = tomllib.loads(config)
    assert Path(parsed['Instance0']['SaveFilePath']).resolve().is_relative_to(OUT.resolve())
    config_path = RUNTIME/'melonDS.toml'
    if not config_path.exists():
        config_path.write_text(config, encoding='utf-8')
    launcher = '@echo off\r\ncd /d "%~dp0runtime"\r\nstart "" "%~dp0runtime\\melonDS.exe" "%~dp0ChibiRobo_B62J_KO_probe_v01.nds"\r\n'
    (OUT/'Run_Hangul_Probe.cmd').write_bytes(launcher.encode('ascii'))
    report = json.loads((ROOT/'metadata/probe_build.json').read_text(encoding='utf-8'))
    report['emulator_preparation'] = {
        'source': str(SOURCE), 'local_copy': str(RUNTIME.relative_to(ROOT)),
        'initial_copy_sha256': hashes, 'save_directory': str((OUT/'saves').relative_to(ROOT)),
        'existing_config_or_saves_modified': False, 'launched': False,
        'launch_script': 'work/output-probe/Run_Hangul_Probe.cmd',
        'configuration_parsed': True,
        'save_directory_runtime_verified': False
    }
    (ROOT/'metadata/probe_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'README.txt').write_text('어서와! 치비로보! 한글 출력 시험 v01\n\nRun_Hangul_Probe.cmd를 실행하세요. 기존 설치본을 복사한 별도 melonDS 환경입니다.\n방향 WASD / A 버튼 J / B 버튼 K / 시작 Enter / 터치 마우스\n\n새 게임을 시작해 초반 대사를 확인해주세요.\n시험 문구: 이제야 왔구나? / 꼬마야 (줄바꿈) 한참 기다렸어!\n문구의 실제 등장 순서와 장면은 아직 확인하지 못했습니다.\n세 번째 시험 문구(데이터를 복사했습니다)는 저장 데이터 복사 완료 메시지입니다. 첫 확인에 복사 작업은 필요하지 않습니다.\n\n일본어 타이틀·메뉴가 남는 것은 정상입니다. 전체 번역판이 아닙니다.\n첫 대사 화면 캡처가 있으면 한글 출력 및 잘림을 확인할 수 있습니다.\n부팅 및 게임 내 출력은 아직 미검증입니다.\n',encoding='utf-8')
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>한글 출력 시험 v01</title><style>body{margin:0;background:#f2f3eb;color:#253329;font:17px/1.8 system-ui}main{max-width:1050px;margin:auto;padding:36px}section{background:white;border-radius:12px;padding:24px;margin:24px 0}a{color:#276344}code{overflow-wrap:anywhere}.pending{color:#895213}.row{display:flex;gap:30px;flex-wrap:wrap}img{image-rendering:pixelated;max-width:100%}</style><main><small>어서와! 치비로보! 해피리치 대청소! · B62J Rev 0</small><h1>한글 출력 시험 v01</h1><p>한글 22자 · 일반 폰트 4종 · 시험 문구 3개</p><section><h2>실행</h2><p><a href="Run_Hangul_Probe.cmd">시험용 melonDS 실행 파일</a> · <a href="ChibiRobo_B62J_KO_probe_v01.nds">시험 ROM</a> · <a href="README.txt">확인 안내</a></p><p>실행 파일 링크가 열리지 않으면 이 폴더의 <b>Run_Hangul_Probe.cmd</b>를 직접 실행하세요. 기존 설치본을 복사한 별도 환경이며 저장 폴더도 이 시험 폴더 아래로 지정했습니다.</p><p>방향 WASD · A 버튼 J · B 버튼 K · 시작 Enter · 터치는 마우스</p><ol><li>새 게임으로 시작합니다. 일본어 타이틀과 메뉴가 남는 것은 정상입니다.</li><li>초반 대사에서 아래 한글 문구가 나오는지 확인합니다. 실제 등장 장면과 순서는 아직 미확인입니다.</li><li>첫 대사 화면을 캡처해 전달해 주세요. 한글이 안 보이거나 게임이 멈추면 해당 화면도 확인에 도움이 됩니다.</li></ol></section><section><h2>예상 문구</h2><p class="pending">아래 이미지는 폰트 파일에서 만든 미리보기입니다. 게임 캡처가 아닙니다.</p>'''
    for idx, text in [(2,'이제야 왔구나?'),(3,'꼬마야 / 한참 기다렸어!')]:
        path=f'../hangul-probe-prep/Font_normal-MsgResFamily-{idx}-korean.png'
        from PIL import Image
        with Image.open(OUT/path) as im:
            w,h=im.size
        page+=f'<p>{html.escape(text)}</p><div class="row"><div>1배<br><img src="{path}" width="{w}" height="{h}"></div><div>3배<br><img src="{path}" width="{w*3}" height="{h*3}"></div></div>'
    page+='''<p>저장 데이터 복사 완료 메시지에도 “데이터를 복사했습니다”를 넣었습니다. 첫 확인에서는 복사 작업을 할 필요가 없습니다.</p></section><section><h2>파일 검증 완료</h2><ul><li>64 MiB 원본 크기 유지, 원본 ROM 해시 동일.</li><li>여유 영역에 자원 6개를 넣고 FAT 6항목·사용 크기·헤더 체크섬만 갱신.</li><li>비대상 파일 3,999개 및 실행 코드·오버레이·파일명 목록 보존.</li><li>저장한 ROM 재읽기, 삽입 파일 일치 및 헤더 CRC16 검사 통과.</li></ul><p class="pending">현재 도구로 melonDS 화면을 조작·관찰할 수 없어 부팅과 실제 한글 출력은 미확인입니다. 1,024 이상 글리프 번호 처리, 실제 창 잘림, 폰트별 출력도 실행 시험이 필요합니다.</p><p><a href="../../metadata/probe_build.json">빌드 검증 기록</a> · <a href="../hangul-probe-prep/index.html">폰트·문구 준비 비교판</a></p></section></main></html>'''
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print('Prepared isolated emulator, launcher, and review; emulator not launched.')


if __name__ == '__main__':
    main()
