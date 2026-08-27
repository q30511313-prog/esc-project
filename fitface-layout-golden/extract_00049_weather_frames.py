#!/usr/bin/env python3
"""Fingerprint every live weather frame referenced by Samsung 00049/style0 seq69."""

import hashlib
import json
from pathlib import Path
import struct
import sys


def u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]


def i16(data, offset):
    return struct.unpack_from('<h', data, offset)[0]


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def directory(container):
    entries = {}
    for index in range(u32(container, 12)):
        record = 32 + index * 74
        raw = container[record:record + 74]
        path = raw[:64].split(b'\0', 1)[0].decode('utf-8', 'replace')
        offset = u32(raw, 64)
        size = u32(raw, 68)
        entries[Path(path).name] = container[offset:offset + size]
    return entries


def images(style):
    start = u32(style, 20)
    cursor = start
    result = []
    while cursor < len(style):
        if cursor + 12 > len(style):
            raise SystemExit(f'truncated image header at {cursor}')
        width = u16(style, cursor)
        height = u16(style, cursor + 2)
        fmt = u16(style, cursor + 4)
        reserved = u16(style, cursor + 6)
        data_size = u32(style, cursor + 8)
        end = cursor + 12 + data_size
        if width <= 0 or height <= 0 or end > len(style):
            raise SystemExit(f'invalid image record at {cursor}')
        record = style[cursor:end]
        result.append({
            'index': len(result),
            'recordOffset': cursor,
            'relativeOffset': cursor - start,
            'width': width,
            'height': height,
            'format': fmt,
            'reserved': reserved,
            'dataSize': data_size,
            'recordSize': len(record),
            'recordSha256': hashlib.sha256(record).hexdigest(),
            'payloadSha256': hashlib.sha256(style[cursor + 12:end]).hexdigest(),
        })
        cursor = end
    if cursor != len(style):
        raise SystemExit('image section did not end exactly at style boundary')
    return result


def widgets(style):
    image_start = u32(style, 20)
    cursor = 24
    result = []
    while cursor < image_start:
        widget_type = u32(style, cursor)
        sequence = u32(style, cursor + 4)
        index_size = u32(style, cursor + 12)
        record_size = index_size & 0xFFFF
        global_index = index_size >> 16
        if record_size < 36 or cursor + record_size > image_start:
            raise SystemExit(f'invalid widget record at {cursor}')
        frame_count = u32(style, cursor + 32) if widget_type == 3 else None
        words = [
            u32(style, cursor + 36 + index * 4)
            for index in range((record_size - 36) // 4)
        ]
        result.append({
            'recordOffset': cursor,
            'globalIndex': global_index,
            'type': widget_type,
            'sequence': sequence,
            'x': i16(style, cursor + 24),
            'y': i16(style, cursor + 26),
            'width': u16(style, cursor + 28),
            'height': u16(style, cursor + 30),
            'frameCount': frame_count,
            'words': words,
        })
        cursor += record_size
    if cursor != image_start:
        raise SystemExit('widget section did not end exactly at image section')
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: extract_00049_weather_frames.py CONTAINER_BIN')
    container_path = Path(sys.argv[1])
    container = container_path.read_bytes()
    style = directory(container)['style0.bin']
    image_records = images(style)
    weather = [
        record for record in widgets(style)
        if record['type'] == 3 and record['sequence'] == 69
    ]
    if len(weather) != 1:
        raise SystemExit(f'expected exactly one style0 Sprite seq69, found {len(weather)}')
    weather = weather[0]
    if weather['globalIndex'] != 7 or weather['frameCount'] != 24:
        raise SystemExit(
            f'unexpected weather identity: g={weather["globalIndex"]} frames={weather["frameCount"]}'
        )
    pointers = weather['words'][:weather['frameCount']]
    if len(pointers) != 24:
        raise SystemExit(f'weather pointer count is {len(pointers)}, expected 24')
    by_relative = {record['relativeOffset']: record for record in image_records}
    frames = []
    for frame_index, pointer in enumerate(pointers):
        image = by_relative.get(pointer)
        if image is None:
            raise SystemExit(f'weather frame {frame_index} pointer {pointer} does not resolve')
        frames.append({
            'frameIndex': frame_index,
            'pointer': pointer,
            **image,
        })

    pointer_groups = {}
    hash_groups = {}
    for frame in frames:
        pointer_groups.setdefault(str(frame['pointer']), []).append(frame['frameIndex'])
        hash_groups.setdefault(frame['payloadSha256'], []).append(frame['frameIndex'])

    report = {
        'containerSha256': hashlib.sha256(container).hexdigest(),
        'style': 'style0.bin',
        'weather': {
            'globalIndex': weather['globalIndex'],
            'sequence': weather['sequence'],
            'x': weather['x'],
            'y': weather['y'],
            'storedWidth': weather['width'],
            'storedHeight': weather['height'],
            'frameCount': weather['frameCount'],
        },
        'imageRecordCount': len(image_records),
        'frames': frames,
        'reusedPointers': {
            pointer: indices for pointer, indices in pointer_groups.items() if len(indices) > 1
        },
        'duplicatePayloads': {
            digest: indices for digest, indices in hash_groups.items() if len(indices) > 1
        },
    }
    print('WEATHER_FRAME_REPORT_JSON=' + json.dumps(report, separators=(',', ':')))


if __name__ == '__main__':
    main()
