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


def main():
    path = Path(sys.argv[1])
    data = path.read_bytes()
    entry_count = u32(data, 12)
    entries = {}
    for index in range(entry_count):
        record = 32 + index * 74
        raw_path = data[record:record + 64].split(b'\0', 1)[0].decode('utf-8', 'replace')
        offset = u32(data, record + 64)
        size = u32(data, record + 68)
        entries[Path(raw_path).name] = data[offset:offset + size]

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
            'words': [f'0x{word:08X}' for word in words],
        })
        cursor += record_size

    date_composite = [r for r in records if r['globalIndex'] == 1]
    pair_candidates = [r for r in records if r['type'] == 5]
    report = {
        'dateCompositeGlobal1': date_composite,
        'pairCandidates': pair_candidates,
        'remainingAfterSecondsAndAmPm': [
            r for r in pair_candidates
            if r['globalIndex'] not in {9, 15, 16}
        ],
    }
    print('DATE_INVENTORY_JSON=' + json.dumps(report, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
