"""Append six test resources to verified unused ROM padding; retain all code."""
from pathlib import Path
import hashlib
import json
import struct
from ndspy.rom import NintendoDSRom
from ndspy._common import crc16

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/output-probe'
PREP = ROOT / 'work/hangul-probe-prep'
NAMES = ['Font_large.NFTR', 'Font_normal.NFTR', 'Font_small.NFTR',
         'Font_smallsmall.NFTR', 'MsgResFamily.bmg', 'MsgResSys.bmg']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def build(source, replacements):
    """Empty replacement list is a byte-identical no-op, not a repack."""
    rom = NintendoDSRom(source)
    result = bytearray(source)
    fat = u32(source, 0x48)
    count = u32(source, 0x4C) // 8
    ranges = [struct.unpack_from('<II', source, fat + 8*i) for i in range(count)]
    cursor = (max(u32(source, 0x80), max(end for start, end in ranges)) + 511) & ~511
    append_start = cursor
    records = []
    for name, replacement in replacements.items():
        file_id = rom.filenames.idOf(name)
        assert file_id is not None
        old_start, old_end = ranges[file_id]
        end = cursor + len(replacement)
        assert end <= len(source), 'Resource expansion exceeds cartridge padding'
        assert all(v == 255 for v in source[cursor:end]), 'Padding is not empty'
        result[cursor:end] = replacement
        struct.pack_into('<II', result, fat + file_id*8, cursor, end)
        records.append({'file': name, 'id': file_id, 'old_start': old_start,
                        'old_end': old_end, 'new_start': cursor, 'new_end': end,
                        'sha256': sha(replacement)})
        cursor = (end + 511) & ~511
    if records:
        struct.pack_into('<I', result, 0x80, records[-1]['new_end'])
        struct.pack_into('<H', result, 0x15E, crc16(result[:0x15E]))
    reread = NintendoDSRom(bytes(result))
    assert len(reread.files) == len(rom.files) == count
    changed_ids = {r['id'] for r in records}
    for file_id, old_file in enumerate(rom.files):
        if file_id not in changed_ids:
            assert reread.files[file_id] == old_file, file_id
    for rec in records:
        assert reread.files[rec['id']] == replacements[rec['file']]
    for field in ['arm9', 'arm7', 'arm9PostData', 'arm9OverlayTable',
                  'arm7OverlayTable', 'iconBanner']:
        assert getattr(rom, field) == getattr(reread, field), field
    fnt_start, fnt_size = struct.unpack_from('<II', source, 0x40)
    assert source[fnt_start:fnt_start+fnt_size] == result[fnt_start:fnt_start+fnt_size]
    # Restore only the approved changed byte ranges and require whole-ROM equality.
    restored = bytearray(result)
    if records:
        for rec in records:
            off = fat + rec['id']*8
            restored[off:off+8] = source[off:off+8]
        for off, size in [(0x80, 4), (0x15E, 2)]:
            restored[off:off+size] = source[off:off+size]
        restored[append_start:records[-1]['new_end']] = source[append_start:records[-1]['new_end']]
    assert bytes(restored) == source
    assert crc16(result[:0x15E]) == struct.unpack_from('<H', result, 0x15E)[0]
    return bytes(result), records


def main():
    original = json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
    source_path = ROOT/original['file']
    source = source_path.read_bytes()
    assert sha(source) == original['sha256']
    control, empty_records = build(source, {})
    assert control == source and not empty_records
    prepared = json.loads((ROOT/'metadata/hangul_probe_preparation.json').read_text(encoding='utf-8'))
    replacements = {name: (PREP/name).read_bytes() for name in NAMES}
    for font in prepared['fonts']:
        assert sha(replacements[font['file']]) == font['sha256']
    built, records = build(source, replacements)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT/'ChibiRobo_B62J_KO_probe_v01.nds'
    if target.exists():
        assert target.read_bytes() == built, 'Existing build differs; create a new revision'
    else:
        target.write_bytes(built)
    assert target.read_bytes() == built
    assert sha(source_path.read_bytes()) == original['sha256']
    report = {
        'source_sha256': original['sha256'], 'output': str(target.relative_to(ROOT)),
        'output_sha256': sha(built), 'output_size': len(built),
        'method': 'Append resources into verified FF cartridge padding, update six FAT records, used-size and header CRC16 only',
        'replacements': records, 'unchanged_fat_files': 4005-len(records),
        'no_change_build_byte_identical': True, 'rom_readback_verified': True,
        'non_target_files_byte_identical': True, 'code_overlay_tables_banner_fnt_preserved': True,
        'changes_restricted_to_recorded_ranges': True, 'header_crc16_verified': True,
        'source_unchanged': True, 'emulator_boot_verified': False,
        'hangul_runtime_verified': False,
        'runtime_limitation': 'Current session has no node_repl/Computer Use runtime for observing or controlling melonDS'
    }
    (ROOT/'metadata/probe_build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
