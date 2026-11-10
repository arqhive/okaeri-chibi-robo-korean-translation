"""실행 중 한국어 조사 고르기(을/를, 이/가 ...) — 어서와! 치비로보! 해피리치 대청소!(B62J).

전편(피워라! 치비로보! AJBJ)의 tools/particle_patch.py를 이 게임에 맞춘 것.
- 메시지 서식 함수 0x0201E0C0(mode, buf, fmt, va) (ARM)를 부르는 8곳의 BL을 ITCM 래퍼로 돌린다.
- 래퍼(ARM)는 원래 함수를 부른 뒤, 결과 버퍼의 조사 표시 문자를 바로 앞 글자의 받침에 맞게 바꾼다(Thumb 루틴).
- 한글 글자 코드는 「받침 없음 → ㄹ 받침 → 그 밖의 받침」 순서로 배정돼 있어야 한다(build_full_text_v06).
- 래퍼 코드는 ARM9의 새 autoload 구역(ITCM ITCM_BASE)으로 들어간다.
조사 자료: docs/particle-hook-research.md
"""
import struct
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB, KS_MODE_ARM

ITCM_BASE = 0x01FFC840          # 기존 ITCM autoload(bss 포함) 바로 뒤 = OS ITCM 아레나 시작
ITCM_END = 0x02000000
# OS_GetInitArenaLo의 ITCM 아레나 시작 값(리터럴). 게임은 0x01FFC840~0x02000000을 아레나로 쓴다(저장 중 버퍼 등).
# v09는 래퍼를 0x01FFE000(아레나 한가운데)에 둬서 저장할 때 덮어써져 멈췄다(2026-11-07). 래퍼를 아레나 맨 앞에 두고 시작 값을 그 뒤로 민다.
ARENA_LO_LITERAL = 0x0211E938
FORMATTER = 0x0201E0C0
CALL_SITES = [0x0201E090, 0x0201E0B8, 0x020A7D30, 0x020A7D80, 0x020A7E40, 0x020A7EA8, 0x020A8310, 0x020A837C]

# 표시 번호 -> (번역문 표기, 받침 있을 때, 없을 때). 4번 (으)로는 ㄹ 받침을 「받침 없음」으로 친다.
MARKERS = [
    ('을(를)', '을', '를'),
    ('이(가)', '이', '가'),
    ('은(는)', '은', '는'),
    ('과(와)', '과', '와'),
    ('(으)', '으', ''),
    ('(이)', '이', ''),
    ('(이)에', '이', '예'),   # (이)에요의 앞 절반: 이에요 / 예요
    (None, '에', ''),         # 뒤 절반, 항상 6번 뒤
]
EU_INDEX = 4
PLACEHOLDER = 0xE000           # 인코딩 전까지 표시 문자를 대신하는 사용자 영역 문자
PARTICLE_CHARS = '을를이가은는과와으예에'
DIGIT_CLASS = bytes([2, 1, 0, 2, 0, 0, 2, 1, 1, 0])   # 영 일 이 삼 사 오 육 칠 팔 구
SKIP2 = [0x8176, 0x8178, 0x816A, 0x8140]              # 」 』 ） 전각 공백: 앞 글자 기준 유지
DIGIT1 = 0x8740                                        # 서식 함수(mode 3)가 숫자를 0x8740('1')..0x8749('0')로 바꿈
SKIP1 = [0x20, 0x29]                                   # 공백, ')'


def batchim_class(ch):
    """0 = 받침 없음, 1 = ㄹ, 2 = 그 밖의 받침."""
    if not '가' <= ch <= '힣':
        return 0
    final = (ord(ch) - 0xAC00) % 28
    return 0 if final == 0 else (1 if final == 8 else 2)


def to_placeholders(text):
    text = text.replace('(이)에요', chr(PLACEHOLDER + 6) + chr(PLACEHOLDER + 7) + '요')
    for i, (pattern, _, _) in enumerate(MARKERS[:6]):
        text = text.replace(pattern, chr(PLACEHOLDER + i))
    return text


def resolve(text):
    """PC에서 표시 문자를 미리 풀어 보는 용도(검사·미리보기). 게임 동작과 같은 규칙."""
    out = []; cls = 0
    for ch in text:
        o = ord(ch) - PLACEHOLDER
        if 0 <= o < 8:
            thr = 2 if o == EU_INDEX else 1
            a, b = MARKERS[o][1], MARKERS[o][2]
            out.append(a if cls >= thr else b)
            continue
        out.append(ch)
        if ch in ' )」』）　':
            continue
        if ch.isdigit():
            cls = DIGIT_CLASS[int(ch)]
        else:
            cls = batchim_class(ch)
    return ''.join(out)


FIX_SRC = """
fix:
    push {r4, r5, r6, r7, lr}
    mov r1, r0
    mov r2, r0
    movs r3, #0
loop:
    ldrb r4, [r1]
    cmp r4, #0
    beq done
    cmp r4, #0x1a
    bne not_tag
    ldrb r5, [r1, #1]
    cmp r5, #2
    bhs copytag
    movs r5, #2
copytag:
    ldrb r6, [r1]
    strb r6, [r2]
    adds r1, #1
    adds r2, #1
    subs r5, #1
    bne copytag
    b loop
not_tag:
    cmp r4, #0x81
    blo single
    cmp r4, #0xa0
    blo dbl
    cmp r4, #0xe0
    blo single
dbl:
    ldrb r5, [r1, #1]
    lsls r6, r4, #8
    orrs r6, r5
    ldr r7, lit_marker0
    subs r7, r6, r7
    cmp r7, #8
    bhs normal2
    adds r1, #2
    movs r4, #1
    cmp r7, #EU
    bne thresh
    movs r4, #2
thresh:
    ldr r5, lit_table
    lsls r7, r7, #2
    adds r5, r5, r7
    cmp r3, r4
    bhs use_a
    adds r5, #2
use_a:
    ldrh r6, [r5]
    cmp r6, #0
    beq loop
    lsrs r4, r6, #8
    strb r4, [r2]
    strb r6, [r2, #1]
    adds r2, #2
    b loop
normal2:
    strb r4, [r2]
    strb r5, [r2, #1]
    adds r1, #2
    adds r2, #2
    ldr r7, lit_d1
    subs r5, r6, r7
    cmp r5, #10
    bhs not_digit2
    adds r5, #1
    cmp r5, #10
    bne digit2
    movs r5, #0
digit2:
    ldr r7, lit_digits
    ldrb r3, [r7, r5]
    b loop
not_digit2:
    ldr r7, lit_s0
    cmp r6, r7
    beq loop
    ldr r7, lit_s1
    cmp r6, r7
    beq loop
    ldr r7, lit_s2
    cmp r6, r7
    beq loop
    ldr r7, lit_s3
    cmp r6, r7
    beq loop
    ldr r7, lit_h0
    cmp r6, r7
    blo cls0
    ldr r7, lit_h1
    cmp r6, r7
    bhi cls0
    movs r3, #2
    ldr r7, lit_t2
    cmp r6, r7
    bhs loop
    movs r3, #1
    ldr r7, lit_t1
    cmp r6, r7
    bhs loop
cls0:
    movs r3, #0
    b loop
single:
    strb r4, [r2]
    adds r1, #1
    adds r2, #1
    cmp r4, #S1A
    beq loop
    cmp r4, #S1B
    beq loop
    subs r5, r4, #0x30
    cmp r5, #10
    bhs cls0
    ldr r6, lit_digits
    ldrb r3, [r6, r5]
    b loop
done:
    strb r4, [r2]
    pop {r4, r5, r6, r7, pc}
    .align 2
lit_marker0: .word MARKER0
lit_table:   .word TABLE
lit_digits:  .word DIGITS
lit_d1: .word D1
lit_s0: .word S0
lit_s1: .word S1
lit_s2: .word S2
lit_s3: .word S3
lit_h0: .word H0
lit_h1: .word H1
lit_t1: .word T1
lit_t2: .word T2
"""


def assemble(marker0, h0, h1, t1, t2, code_of):
    """ITCM 덩어리: ARM 래퍼, Thumb 루틴, 조사 표, 숫자 표. code_of: 한글 글자 -> 게임 글자 코드."""
    table = b''.join(struct.pack('<HH', code_of(a) if a else 0, code_of(b) if b else 0) for _, a, b in MARKERS)
    arm = Ks(KS_ARCH_ARM, KS_MODE_ARM); th = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    WRAP_LEN = 32
    fix_addr = ITCM_BASE + WRAP_LEN
    wrap_src = f"""
        push {{r1, lr}}
        bl {FORMATTER:#x}
        pop {{r1}}
        push {{r0}}
        mov r0, r1
        blx {fix_addr | 1:#x}
        pop {{r0}}
        pop {{pc}}
    """
    wrap = bytes(arm.asm(wrap_src, ITCM_BASE)[0]); assert len(wrap) == WRAP_LEN, len(wrap)

    def fix_bytes(table_addr, digits_addr):
        s = FIX_SRC
        for k, v in {'MARKER0': marker0, 'TABLE': table_addr, 'DIGITS': digits_addr, 'D1': DIGIT1, 'S0': SKIP2[0], 'S1': SKIP2[1],
                     'S2': SKIP2[2], 'S3': SKIP2[3], 'H0': h0, 'H1': h1, 'T1': t1, 'T2': t2}.items():
            s = s.replace(' ' + k + '\n', f' {v:#x}\n')
        s = s.replace('#EU\n', f'#{EU_INDEX}\n').replace('#S1A\n', f'#{SKIP1[0]:#x}\n').replace('#S1B\n', f'#{SKIP1[1]:#x}\n')
        return bytes(th.asm(s, fix_addr)[0])
    first = fix_bytes(0, 0)
    table_addr = fix_addr + len(first); digits_addr = table_addr + len(table)
    fix = fix_bytes(table_addr, digits_addr); assert len(fix) == len(first)
    blob = wrap + fix + table + DIGIT_CLASS
    blob += bytes((-len(blob)) % 4)
    assert ITCM_BASE + len(blob) <= ITCM_END
    return blob, {'wrapper': hex(ITCM_BASE), 'fix': hex(fix_addr), 'table': hex(table_addr), 'digits': hex(digits_addr), 'size': len(blob)}


def arm_bl(src, dst):
    off = (dst - (src + 8)) >> 2
    assert -(1 << 23) <= off < (1 << 23)
    return struct.pack('<I', 0xEB000000 | (off & 0xFFFFFF))


def patch_calls(main, base=0x02000000):
    """주 구역(ARM9 0x02000000)의 서식 함수 호출 8곳을 래퍼로."""
    out = bytearray(main)
    for site in CALL_SITES:
        o = site - base
        assert bytes(out[o:o + 4]) == arm_bl(site, FORMATTER), hex(site)
        out[o:o + 4] = arm_bl(site, ITCM_BASE)
    return bytes(out)


def apply_to_rom(rom_bytes, info):
    """빌드된 ROM에 조사 패치를 넣는다.
    - ARM9: 호출 8곳을 래퍼로, ITCM autoload 구역 추가, 다시 압축해 원래 자리(0x4000)에 둔다.
    - ARM9가 커지므로 바로 뒤의 ARM9 오버레이 표를 카트리지 빈 공간(마지막 파일 뒤)으로 옮긴다.
    info: fulltext_build의 particles(h0,t1,t2,h1,marker0,particle_char_codes; 16진 문자열)."""
    from ndspy.rom import NintendoDSRom
    import ndspy.code as code
    u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]
    out = bytearray(rom_bytes)
    rom = NintendoDSRom(bytes(rom_bytes))
    m = rom.loadArm9()
    assert [hex(s.ramAddress) for s in m.sections] == ['0x2000000', '0x1ff8000', '0x27e0000'], 'unexpected ARM9 sections'
    itcm = m.sections[1]; assert itcm.ramAddress + len(itcm.data) + itcm.bssSize <= ITCM_BASE
    pcodes = {c: int(v, 16) for c, v in info['particle_char_codes'].items()}
    blob, layout = assemble(int(info['marker0'], 16), int(info['h0'], 16), int(info['h1'], 16), int(info['t1'], 16), int(info['t2'], 16), lambda c: pcodes[c])
    main = bytearray(patch_calls(bytes(m.sections[0].data)))
    lit = ARENA_LO_LITERAL - 0x02000000
    assert struct.unpack_from('<I', main, lit)[0] == ITCM_BASE, 'ITCM arena literal mismatch'
    arena_lo = (ITCM_BASE + len(blob) + 0x1F) & ~0x1F
    struct.pack_into('<I', main, lit, arena_lo)
    m.sections[0].data = main
    m.sections.insert(2, code.MainCodeFile.Section(blob, ITCM_BASE, 0))
    arm9 = m.save(compress=True)
    post = rom.arm9PostData
    arm9_off, arm9_size = u32(out, 0x20), u32(out, 0x2C)
    ov_off, ov_size = u32(out, 0x50), u32(out, 0x54)
    assert out[arm9_off + arm9_size: arm9_off + arm9_size + len(post)] == post
    fat = u32(out, 0x48); n = u32(out, 0x4C) // 8
    next_file = min(s for s in (u32(out, fat + 8 * i) for i in range(n)) if s > arm9_off)
    # 오버레이 표를 빈 공간으로
    cursor = (u32(out, 0x80) + 0x1FF) & ~0x1FF
    table = bytes(out[ov_off:ov_off + ov_size])
    assert all(v == 0xFF for v in out[cursor:cursor + ov_size]), 'no padding for overlay table'
    out[cursor:cursor + ov_size] = table
    struct.pack_into('<I', out, 0x50, cursor)
    struct.pack_into('<I', out, 0x80, cursor + ov_size)
    # ARM9를 원래 자리에, 뒤에 Nitro 꼬리표
    end = arm9_off + len(arm9) + len(post)
    assert end <= next_file, ('ARM9 too large', hex(end), hex(next_file))
    out[arm9_off:next_file] = b'\xFF' * (next_file - arm9_off)
    out[arm9_off:arm9_off + len(arm9)] = arm9
    out[arm9_off + len(arm9):end] = post
    struct.pack_into('<I', out, 0x2C, len(arm9))
    from build_hangul_probe import crc16
    struct.pack_into('<H', out, 0x15E, crc16(bytes(out[:0x15E])))
    # 다시 읽어 확인
    re = NintendoDSRom(bytes(out)); m2 = re.loadArm9()
    assert [hex(s.ramAddress) for s in m2.sections] == ['0x2000000', '0x1ff8000', hex(ITCM_BASE), '0x27e0000']
    assert bytes(m2.sections[2].data) == blob
    for site in CALL_SITES:
        assert bytes(m2.sections[0].data[site - 0x02000000:site - 0x02000000 + 4]) == arm_bl(site, ITCM_BASE)
    assert re.arm9OverlayTable == rom.arm9OverlayTable and re.files == rom.files and re.arm7 == rom.arm7
    secure_same = bytes(arm9[:0x800]) == bytes(rom.arm9[:0x800])
    assert struct.unpack_from('<I', m2.sections[0].data, lit)[0] == arena_lo
    return bytes(out), dict(layout, itcm_arena_lo=hex(arena_lo), arm9_old_size=arm9_size, arm9_new_size=len(arm9), arm9_room=next_file - arm9_off - len(post),
                            overlay_table_moved_to=hex(cursor), secure_area_unchanged=secure_same)
