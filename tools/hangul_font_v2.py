"""한글 글자를 게임 NFTR에 넣는 방식 v2 (2026-11-07).

v1(prepare_hangul_probe.expand)의 문제:
- 글자마다 잉크 아래 끝을 칸 바닥에 붙여서(h-gh), 받침 없는 글자와 있는 글자의 높이가 1px씩 어긋났다.
- 글자를 칸 가운데에 두고 폭 정보를 (0,w,w)로 고정해서, 간격이 일본어 한자(1,w,w+1)보다 1px 좁았고 글자마다 들쭉날쭉했다.

v2:
- 모든 글자를 같은 펜 위치에서 그려, 글꼴 전체에서 가장 높은 잉크 윗줄을 칸 0행에 맞춘다(기준선 공통).
- 잉크는 칸 왼쪽 0열부터 넣고, 폭 정보는 (잉크 왼쪽 여백, 잉크 폭, 글꼴 advance)로 글자마다 기록한다.
그 밖의 처리(코드 매핑, 블록 재배치, 기존 글자 보존 검사)는 v1과 같다.
"""
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from prepare_hangul_probe import FONTDIR, parsefont, align
from analyze_text_fonts import u16, u32


def render(font, char):
    tmp = Image.new('1', (48, 48)); d = ImageDraw.Draw(tmp); d.fontmode = '1'; d.text((8, 8), char, font=font, fill=1)
    box = tmp.getbbox(); assert box, char
    return tmp, box


def expand_v2(b, codes, spec):
    bs, mp, ci, wi, count, cell = parsefont(b); w, h = b[ci + 8:ci + 10]
    assert b[ci + 14] == 1 and u16(b, wi + 8) == 0; assert sum(k == 'HDWC' for k, o, n in bs) == 1
    font = ImageFont.truetype(str(FONTDIR / (spec[0] + '.ttf')), spec[1])
    blank = {c for c in codes if ord(c) >= 0xE000}            # 조사 표시 문자: 빈 글자(폭 0). 게임이 실행 중에 바꿔 넣는다.
    drawn = {c: render(font, c) for c in codes if c not in blank}
    top = min(box[1] for _, box in drawn.values())          # 공통 윗줄
    newglyphs = []; widths = []; previews = {}
    for char in codes:
        if char in blank:
            newglyphs.append(bytes(1) * cell); widths.append(bytes([0, 0, 0])); continue
        tmp, box = drawn[char]; g = tmp.crop(box); gw, gh = g.size; dy = box[1] - top
        assert gw <= w and dy + gh <= h, (char, spec, box, w, h, dy)
        left = box[0] - 8; adv = round(font.getlength(char))
        assert 0 <= left < 128 and adv <= 255
        im = Image.new('1', (w, h)); im.paste(g, (0, dy))
        raw = np.packbits(np.array(im, dtype=np.uint8).reshape(-1)).tobytes(); assert len(raw) <= cell
        newglyphs.append(raw.ljust(cell, b'\0')); widths.append(bytes([left, gw, adv]))
        previews[char] = im.convert('L').point(lambda v: 255 - v)
    chunks = []
    full_maps = [o for k, o, n in bs if k == 'PAMC' and u16(b, o + 8) == 0 and u16(b, o + 10) == 65535 and u16(b, o + 12) == 2]
    assert len(full_maps) == 1, 'Expected one full-range sparse mapping'
    full_map = full_maps[0]
    for k, o, n in bs:
        q = bytearray(b[o:o + n])
        if k == 'PLGC': q = bytearray(align(bytes(q[:16 + count * cell]) + b''.join(newglyphs)))
        if k == 'HDWC':
            q = bytearray(align(bytes(q[:16 + count * 3]) + b''.join(widths))); struct.pack_into('<H', q, 10, count + len(codes) - 1)
        if o == full_map:
            pairs = dict(struct.unpack_from('<HH', b, o + 22 + 4 * i) for i in range(u16(b, o + 20)))
            assert not (set(codes.values()) & set(mp)), 'New character codes must be unused'
            pairs.update((code, count + i) for i, code in enumerate(codes.values()))
            q = bytearray(align(bytes(q[:20]) + struct.pack('<H', len(pairs)) + b''.join(struct.pack('<HH', c, g) for c, g in sorted(pairs.items()))))
        struct.pack_into('<I', q, 4, len(q)); chunks.append((k, o, q))
    offsets = {}; pos = 16
    for k, o, q in chunks: offsets[o] = pos; pos += len(q)
    for k, o, q in chunks:
        if k == 'FNIF':
            for off in (16, 20, 24): struct.pack_into('<I', q, off, offsets[u32(q, off) - 8] + 8)
        if k == 'HDWC' and u32(q, 12): struct.pack_into('<I', q, 12, offsets[u32(q, 12) - 8] + 8)
        if k == 'PAMC':
            nxt = u32(q, 16); struct.pack_into('<I', q, 16, offsets[nxt - 8] + 8 if nxt else 0)
    header = bytearray(b[:16]); struct.pack_into('<I', header, 8, pos); struct.pack_into('<H', header, 14, len(chunks))
    result = bytes(header) + b''.join(bytes(q) for _, _, q in chunks)
    nbs, nmp, nci, nwi, ncount, ncell = parsefont(result)
    assert ncount == count + len(codes); assert all(nmp[c] == g for c, g in mp.items())
    assert result[nci + 16:nci + 16 + count * cell] == b[ci + 16:ci + 16 + count * cell]
    assert result[nwi + 16:nwi + 16 + count * 3] == b[wi + 16:wi + 16 + count * 3]
    for i, (ch, code) in enumerate(codes.items()): assert nmp[code] == count + i
    advs = sorted({x[2] for x in widths}); lefts = sorted({x[0] for x in widths})
    return result, previews, {'cell': [w, h], 'old_glyphs': count, 'new_glyphs': ncount, 'added_glyphs': len(codes),
                              'old_glyph_bytes_preserved': True, 'old_width_entries_preserved': True, 'old_code_mappings_preserved': True,
                              'old_size': len(b), 'new_size': len(result), 'font_family': spec[0], 'font_px': spec[1],
                              'placement': 'v2 common top line, per-glyph width (left, ink width, font advance)',
                              'hangul_advances': advs, 'hangul_left_offsets': lefts}


def widen_advance(b, code, extra):
    """기존 글자 하나의 advance(다음 글자까지 간격)만 extra px 늘린다. 글자 모양·왼쪽 여백·잉크 폭은 그대로."""
    bs, mp, ci, wi, count, cell = parsefont(b); g = mp[code]
    q = bytearray(b); off = wi + 16 + 3 * g
    assert q[off + 2] + extra <= 255
    q[off + 2] += extra
    return bytes(q), {'code': hex(code), 'glyph': g, 'old': list(b[off:off + 3]), 'new': list(q[off:off + 3])}


DIGITS_FONT = {0x8740 + i: '1234567890'[i] for i in range(10)}      # 게임이 대사 숫자를 바꿔 그리는 전용 숫자(1..9,0)
DIGITS_ASCII = {0x30 + i: str(i) for i in range(10)}
DIGITS_FULL = {0x824F + i: '０１２３４５６７８９'[i] for i in range(10)}


def replace_glyphs(b, code_chars, spec, ref='가'):
    """기존 글자(코드는 그대로)의 모양·폭을 갈무리로 바꾼다. 윗줄은 한글(ref)과 같은 기준."""
    bs, mp, ci, wi, count, cell = parsefont(b); w, h = b[ci + 8:ci + 10]
    font = ImageFont.truetype(str(FONTDIR / (spec[0] + '.ttf')), spec[1])
    top = render(font, ref)[1][1]
    q = bytearray(b); recs = []
    for code, char in code_chars.items():
        g = mp[code]; tmp, box = render(font, char); gl = tmp.crop(box); gw, gh = gl.size; dy = box[1] - top
        assert gw <= w and 0 <= dy and dy + gh <= h, (char, spec, box, w, h, dy)
        im = Image.new('1', (w, h)); im.paste(gl, (0, dy))
        raw = np.packbits(np.array(im, dtype=np.uint8).reshape(-1)).tobytes().ljust(cell, b'\0')[:cell]
        q[ci + 16 + g * cell: ci + 16 + (g + 1) * cell] = raw
        wo = wi + 16 + 3 * g; old = list(q[wo:wo + 3]); q[wo:wo + 3] = bytes([box[0] - 8, gw, round(font.getlength(char))])
        recs.append({'code': hex(code), 'char': char, 'old_width': old, 'new_width': list(q[wo:wo + 3])})
    return bytes(q), recs
