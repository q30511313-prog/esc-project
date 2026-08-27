#!/usr/bin/env python3
"""Render Samsung 00049 weather alpha masks as compact ASCII for semantic review."""

from pathlib import Path
import struct
import sys


def u16(data, offset): return struct.unpack_from('<H', data, offset)[0]
def u32(data, offset): return struct.unpack_from('<I', data, offset)[0]


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


def image_records(style):
    start = u32(style, 20)
    cursor = start
    result = {}
    while cursor < len(style):
        width = u16(style, cursor)
        height = u16(style, cursor + 2)
        fmt = u16(style, cursor + 4)
        data_size = u32(style, cursor + 8)
        end = cursor + 12 + data_size
        result[cursor - start] = (cursor, width, height, fmt, data_size)
        cursor = end
    return result


def weather_pointers(style):
    image_start = u32(style, 20)
    cursor = 24
    while cursor < image_start:
        widget_type = u32(style, cursor)
        sequence = u32(style, cursor + 4)
        record_size = u32(style, cursor + 12) & 0xFFFF
        if widget_type == 3 and sequence == 69:
            count = u32(style, cursor + 32)
            return [u32(style, cursor + 36 + i * 4) for i in range(count)]
        cursor += record_size
    raise SystemExit('weather seq69 not found')


def alpha_grid(style, image):
    cursor, width, height, fmt, data_size = image
    if fmt != 0x0080 or width != 30 or height != 30 or data_size < width * height * 3:
        raise SystemExit(f'unexpected weather image schema {width}x{height} fmt=0x{fmt:04X}')
    pixels = style[cursor + 12:cursor + 12 + width * height * 3]
    return [[pixels[(y * width + x) * 3 + 2] for x in range(width)] for y in range(height)]


def compact_ascii(alpha):
    chars = ' .:+#'
    lines = []
    for by in range(0, 30, 2):
        line = []
        for bx in range(0, 30, 2):
            values = [alpha[y][x] for y in range(by, min(by + 2, 30)) for x in range(bx, min(bx + 2, 30))]
            value = max(values)
            index = 0 if value < 16 else 1 if value < 64 else 2 if value < 128 else 3 if value < 224 else 4
            line.append(chars[index])
        lines.append(''.join(line).rstrip())
    return lines


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: dump_00049_weather_ascii.py CONTAINER_BIN')
    container = Path(sys.argv[1]).read_bytes()
    style = directory(container)['style0.bin']
    images = image_records(style)
    pointers = weather_pointers(style)
    if len(pointers) != 24:
        raise SystemExit(f'expected 24 weather pointers, found {len(pointers)}')
    for index, pointer in enumerate(pointers):
        image = images.get(pointer)
        if image is None:
            raise SystemExit(f'frame {index} pointer {pointer} does not resolve')
        print(f'=== WEATHER_FRAME_{index:02d} ===')
        for line in compact_ascii(alpha_grid(style, image)):
            print(line)


if __name__ == '__main__':
    main()
