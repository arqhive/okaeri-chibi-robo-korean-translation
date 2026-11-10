"""ARM9 코드 문자열 4묶음 대조판(2026-11-11).
실기 결과: v44(ARM9 문자열 92곳 바꿈) 오류, B(ARM9 원본·오버레이만) 정상, C(B + ARM9 원본을 다시 압축만) 정상.
→ ARM9 문자열 92곳 중 원인을 가르려고, 주소 순서로 4묶음(23곳씩)으로 나눠 「묶음 하나만 원문으로 두고 나머지는 번역」한 롬 X1~X4를 만든다
  (묶음 하나만 번역한 판은 Q2·Q3에서 다시 압축한 ARM9이 오버레이 표 앞 자리를 넘침). 원인 묶음을 뺀 판만 정상이어야 한다.
나머지는 대조판 B와 같음(대사 v26·그림·배너·오버레이 코드 문자열, 헤더 0x80 원본, 조사 패치 없음)."""
from pathlib import Path
import json, hashlib, struct
import ndspy._common
from ndspy.rom import NintendoDSRom
import overlay_text_patch as OTP
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'work/output-bisect/ChibiRobo_B62J_KO_test_B_ovonly_v44.nds'
def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def build_with(base, jobs):
    out = bytearray(base); r0 = NintendoDSRom(base); m = r0.loadArm9()
    main = bytearray(m.sections[0].data)
    for j in jobs: OTP._put(main, 0x02000000, j)
    m.sections[0].data = main
    arm9 = m.save(compress=True); post = r0.arm9PostData
    off, size = u32(out, 0x20), u32(out, 0x2C); assert out[off + size:off + size + len(post)] == post
    lim = u32(out, 0x50); end = off + len(arm9) + len(post); assert end <= lim
    out[off:lim] = b'\xFF' * (lim - off); out[off:off + len(arm9)] = arm9; out[off + len(arm9):end] = post
    struct.pack_into('<I', out, 0x2C, len(arm9)); struct.pack_into('<H', out, 0x15E, ndspy._common.crc16(bytes(out[:0x15E])))
    r = NintendoDSRom(bytes(out)); d = bytes(r.loadArm9().sections[0].data); d0 = bytes(r0.loadArm9().sections[0].data)
    for j in jobs:
        k = j['ram'] - 0x02000000; assert d[k:k + len(j['src'])] == j['dst'] + bytes(len(j['src']) - len(j['dst']))
    allowed = set()
    for j in jobs: k = j['ram'] - 0x02000000; allowed.update(range(k, k + len(j['src'])))
    allowed.update(range(0xBB4, 0xBB8))  # 모듈 정보의 압축 끝 주소(다시 압축하면 바뀜, v44 검사에서 확인)
    assert all(i in allowed for i in range(len(d)) if d[i] != d0[i])
    assert r.files == r0.files and r.arm9OverlayTable == r0.arm9OverlayTable
    return bytes(out), len(arm9)
def main():
    base = B.read_bytes()
    J = sorted([j for j in OTP.jobs('metadata/fulltext_build_v26.json') if j['where'] == 'arm9'], key=lambda j: j['ram'])
    assert len(J) == 92
    groups = [J[:i * 23] + J[(i + 1) * 23:] for i in range(4)]; kept = [J[i * 23:(i + 1) * 23] for i in range(4)]
    rec = []
    for n, g in enumerate(groups, 1):
        data, size = build_with(base, g)
        p = ROOT / f'work/output-bisect/ChibiRobo_B62J_KO_test_X{n}_arm9.nds'; p.write_bytes(data)
        rec.append(dict(name=f'X{n}', file=str(p.relative_to(ROOT)), md5=hashlib.md5(data).hexdigest(), arm9_compressed_size=hex(size),
                        kept_original_first=hex(kept[n-1][0]['ram']), kept_original_last=hex(kept[n-1][-1]['ram']), kept_original=[dict(ram=hex(j['ram']), jp=j['jp'], ko=j['ko']) for j in kept[n-1]], translated_count=len(g)))
    (ROOT / 'metadata/test_arm9_quarters_build.json').write_text(json.dumps(dict(base='test_B_ovonly_v44', original_arm9_size='0xc8bc4', groups=rec, runtime_verified=False), ensure_ascii=False, indent=2) + '\n', 'utf8')
    for x in rec: print(x['name'], x['kept_original_first'], x['kept_original_last'], x['arm9_compressed_size'], x['md5'])
if __name__ == '__main__': main()
