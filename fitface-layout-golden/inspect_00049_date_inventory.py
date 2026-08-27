#!/usr/bin/env python3
import json
import struct
import sys
from pathlib import Path


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def i16(b, o):
    return struct.unpack_from('<h', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def words32(blob):
    return [
        f'0x{u32(blob, offset):08X}'
        for offset in range(0, len(blob) - (len(blob) % 4), 4)
    ]


def printable_ascii(blob):
    return ''.join(chr(byte) if 32 <= byte < 127 else '.' for byte in blob)


def main():
    path = Path(sys.argv[1])
    data = path.read_bytes()
    entry_count = u32(data, 12)
    entries = {}
    entry_meta = {}
    for index in range(entry_count):
        record = 32 + index * 74
        raw_path = data[record:record + 64].split(b'\0', 1)[0].decode('utf-8', 'replace')
        offset = u32(data, record + 64)
        size = u32(data, record + 68)
        name = Path(raw_path).name
        entries[name] = data[offset:offset + size]
        entry_meta[name] = {'index': index, 'path': raw_path, 'offset': offset, 'size': size}

    style = entries['style0.bin']
    image_offset = u32(style, 20)
    cursor = 24
    records = []
    while cursor < image_offset:
        widget_type = u32(style, cursor)
        sequence = u32(style, cursor + 4)
        index_size = u32(style, cursor + 12)
        record_size = index_size & 0xFFFF
        global_index = index_size >> 16
        words = [
            u32(style, cursor + 36 + word * 4)
            for word in range((record_size - 36) // 4)
        ]
        records.append({
            'globalIndex': global_index,
            'type': widget_type,
            'sequence': sequence,
            'x': i16(style, cursor + 24),
            'y': i16(style, cursor + 26),
            'width': u16(style, cursor + 28),
            'height': u16(style, cursor + 30),
            'recordSize': record_size,
            'bindingLowByte': (words[1] & 0xFF) if widget_type == 5 and len(words) > 1 else None,
            'compositeBindingWord': f'0x{words[1]:08X}' if widget_type == 13 and len(words) > 1 else None,
            'word13': f'0x{words[13]:08X}' if len(words) > 13 else None,
            'opaqueArgbWordIndices': [
                index for index, word in enumerate(words)
                if word != 0xFFFFFFFF and (word >> 24) == 0xFF
            ],
            'words': [f'0x{word:08X}' for word in words],
        })
        cursor += record_size

    composite_candidates = [r for r in records if r['type'] == 13]
    pair_candidates = [r for r in records if r['type'] == 5]

    # Composite word1 has the form 0x0008xxxx on Samsung 00049. The low 16-bit
    # binding differentiates the native temperature (7) and battery (9) renderer
    # resources. Dump those exact font entries plus neighboring font entries so the
    # colour path can be proven rather than guessed from a sentinel-heavy record.
    font_names = sorted(name for name in entries if name.startswith('font_') and name.endswith('.bin'))
    font_report = {}
    for name in font_names:
        blob = entries[name]
        font_report[name] = {
            **entry_meta[name],
            'headHex': blob[:128].hex(),
            'headAscii': printable_ascii(blob[:128]),
            'headWords32': words32(blob[:128]),
        }

    report = {
        'compositeCandidates': composite_candidates,
        'targetComposites': [
            r for r in composite_candidates
            if r['globalIndex'] in {1, 8, 11}
        ],
        'pairCandidates': pair_candidates,
        'remainingAfterSecondsAndAmPm': [
            r for r in pair_candidates
            if r['globalIndex'] not in {9, 15, 16}
        ],
        'fontEntries': font_report,
    }
    print('00049_COLOR_INVENTORY_JSON=' + json.dumps(report, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
