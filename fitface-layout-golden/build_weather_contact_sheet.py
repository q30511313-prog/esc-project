#!/usr/bin/env python3
"""Build a dependency-free 24-frame weather contact sheet from a Fit3 container.

Frames are rendered in pointer order from Samsung 00049 style0 g7/type3/seq69.
The sheet is a diagnostic only: 6 columns x 4 rows, indices 00..23 row-major.
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

STYLE_MAGIC = 0x12345678
WIDGET_SPRITE = 3
IMAGE_RGB565_ALPHA = 0x0080
IMAGE_RGB565 = 0x0082
IMAGE_INDEXED8 = 0x0088


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from('<H', data, offset)[0]


def i16(data: bytes, offset: int) -> int:
    return struct.unpack_from('<h', data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from('<I', data, offset)[0]


def container_entries(data: bytes) -> dict[str, bytes]:
    if len(data) < 32 or data[:4] != b'oppo':
        raise SystemExit('input is not a Fit3 oppo container')
    count = u32(data, 12)
    body = 32 + count * 74
    if body > len(data):
        raise SystemExit('truncated Fit3 directory')
    result: dict[str, bytes] = {}
    for index in range(count):
        record = 32 + index * 74
        raw = data[record:record + 64].split(b'\0', 1)[0]
        name = Path(raw.decode('utf-8', 'strict')).name
        offset = u32(data, record + 64)
        size = u32(data, record + 68)
        if offset < body or offset + size > len(data):
            raise SystemExit(f'entry {name} is out of bounds')
        result[name] = data[offset:offset + size]
    return result


def parse_weather_pointers(style: bytes) -> list[int]:
    if len(style) < 24 or u32(style, 0) != STYLE_MAGIC:
        raise SystemExit('style0.bin has an invalid style header')
    declared_count = u32(style, 4)
    image_offset = u32(style, 20)
    cursor = 24
    seen = 0
    match: list[int] | None = None
    while cursor < image_offset:
        if cursor + 36 > image_offset:
            raise SystemExit('truncated style0 widget record')
        widget_type = u32(style, cursor)
        sequence = u32(style, cursor + 4)
        index_size = u32(style, cursor + 12)
        record_size = index_size & 0xFFFF
        global_index = index_size >> 16
        if record_size < 36 or cursor + record_size > image_offset:
            raise SystemExit('invalid style0 widget record size')
        word_count = (record_size - 36) // 4
        words = [u32(style, cursor + 36 + i * 4) for i in range(word_count)]
        if widget_type == WIDGET_SPRITE and global_index == 7 and sequence == 69:
            frame_count = u32(style, cursor + 0x20) & 0x00FFFFFF
            if frame_count > len(words):
                raise SystemExit('weather Sprite frame count exceeds pointer words')
            if match is not None:
                raise SystemExit('weather Sprite identity is ambiguous')
            match = words[:frame_count]
        cursor += record_size
        seen += 1
    if cursor != image_offset or seen != declared_count:
        raise SystemExit('style0 widget stream does not end exactly')
    if match is None:
        raise SystemExit('weather Sprite g7/type3/seq69 was not found')
    if len(match) != 24:
        raise SystemExit(f'expected 24 weather frames, found {len(match)}')
    return match


def parse_images(style: bytes) -> dict[int, tuple[int, int, list[tuple[int, int, int, int]]]]:
    image_offset = u32(style, 20)
    image_bytes = u32(style, 12)
    end = image_offset + image_bytes
    if end != len(style):
        raise SystemExit('style0 image section does not match file size')
    cursor = image_offset
    first = image_offset
    images: dict[int, tuple[int, int, list[tuple[int, int, int, int]]]] = {}
    while cursor < end:
        if cursor + 12 > end:
            raise SystemExit('truncated image header')
        width = u16(style, cursor)
        height = u16(style, cursor + 2)
        fmt = u16(style, cursor + 4)
        data_size = u32(style, cursor + 8)
        payload = cursor + 12
        if width <= 0 or height <= 0 or payload + data_size > end:
            raise SystemExit('invalid image record')
        pixels: list[tuple[int, int, int, int]] = []
        if fmt == IMAGE_INDEXED8:
            expected = 1024 + width * height
            if data_size < expected:
                raise SystemExit('indexed image payload is too small')
            palette = []
            for i in range(256):
                base = payload + i * 4
                blue, green, red, alpha = style[base:base + 4]
                palette.append((red, green, blue, alpha))
            samples = payload + 1024
            pixels = [palette[style[samples + i]] for i in range(width * height)]
        elif fmt in (IMAGE_RGB565, IMAGE_RGB565_ALPHA):
            bpp = 3 if fmt == IMAGE_RGB565_ALPHA else 2
            expected = width * height * bpp
            if data_size < expected:
                raise SystemExit('RGB565 image payload is too small')
            for i in range(width * height):
                base = payload + i * bpp
                value = u16(style, base)
                red = (((value >> 11) & 0x1F) * 255 + 15) // 31
                green = (((value >> 5) & 0x3F) * 255 + 31) // 63
                blue = ((value & 0x1F) * 255 + 15) // 31
                alpha = style[base + 2] if bpp == 3 else 255
                pixels.append((red, green, blue, alpha))
        else:
            raise SystemExit(f'unsupported image format 0x{fmt:04X}')
        images[cursor - first] = (width, height, pixels)
        cursor = payload + data_size
    if cursor != end:
        raise SystemExit('image scan did not end exactly')
    return images


DIGITS = {
    '0': ('111', '101', '101', '101', '111'),
    '1': ('010', '110', '010', '010', '111'),
    '2': ('111', '001', '111', '100', '111'),
    '3': ('111', '001', '111', '001', '111'),
    '4': ('101', '101', '111', '001', '001'),
    '5': ('111', '100', '111', '001', '111'),
    '6': ('111', '100', '111', '101', '111'),
    '7': ('111', '001', '010', '010', '010'),
    '8': ('111', '101', '111', '101', '111'),
    '9': ('111', '101', '111', '001', '111'),
}


def draw_digit(canvas: bytearray, width: int, x: int, y: int, digit: str) -> None:
    for row, pattern in enumerate(DIGITS[digit]):
        for col, bit in enumerate(pattern):
            if bit != '1':
                continue
            for dy in range(2):
                for dx in range(2):
                    px = x + col * 2 + dx
                    py = y + row * 2 + dy
                    pos = (py * width + px) * 3
                    canvas[pos:pos + 3] = bytes((232, 232, 232))


def composite_pixel(dst: tuple[int, int, int], src: tuple[int, int, int, int]) -> tuple[int, int, int]:
    red, green, blue, alpha = src
    if alpha == 255:
        return red, green, blue
    if alpha == 0:
        return dst
    inv = 255 - alpha
    return tuple((src_channel * alpha + dst_channel * inv + 127) // 255 for src_channel, dst_channel in zip((red, green, blue), dst))


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)


def write_png_rgb(path: Path, width: int, height: int, rgb: bytes) -> None:
    rows = bytearray()
    stride = width * 3
    for y in range(height):
        rows.append(0)
        rows.extend(rgb[y * stride:(y + 1) * stride])
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    png.extend(png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)))
    png.extend(png_chunk(b'IDAT', zlib.compress(bytes(rows), 9)))
    png.extend(png_chunk(b'IEND', b''))
    path.write_bytes(png)


def build(container_path: Path, output_path: Path) -> None:
    entries = container_entries(container_path.read_bytes())
    style = entries.get('style0.bin')
    if style is None:
        raise SystemExit('container has no style0.bin')
    pointers = parse_weather_pointers(style)
    images = parse_images(style)
    frames = []
    for index, pointer in enumerate(pointers):
        frame = images.get(pointer)
        if frame is None:
            raise SystemExit(f'weather frame {index} points to missing image offset 0x{pointer:X}')
        frames.append(frame)

    columns, rows = 6, 4
    cell_w, cell_h = 72, 64
    sheet_w, sheet_h = columns * cell_w, rows * cell_h
    background = (30, 32, 35)
    border = (70, 72, 76)
    canvas = bytearray(background * (sheet_w * sheet_h))

    for index, (frame_w, frame_h, pixels) in enumerate(frames):
        col, row = index % columns, index // columns
        cell_x, cell_y = col * cell_w, row * cell_h
        for x in range(cell_x, cell_x + cell_w):
            for y in (cell_y, cell_y + cell_h - 1):
                pos = (y * sheet_w + x) * 3
                canvas[pos:pos + 3] = bytes(border)
        for y in range(cell_y, cell_y + cell_h):
            for x in (cell_x, cell_x + cell_w - 1):
                pos = (y * sheet_w + x) * 3
                canvas[pos:pos + 3] = bytes(border)

        label = f'{index:02d}'
        draw_digit(canvas, sheet_w, cell_x + 4, cell_y + 3, label[0])
        draw_digit(canvas, sheet_w, cell_x + 12, cell_y + 3, label[1])

        origin_x = cell_x + (cell_w - frame_w) // 2
        origin_y = cell_y + 14 + max(0, (cell_h - 14 - frame_h) // 2)
        if origin_x < cell_x + 1 or origin_y < cell_y + 12 or origin_x + frame_w >= cell_x + cell_w:
            raise SystemExit(f'weather frame {index} does not fit contact-sheet cell')
        for py in range(frame_h):
            for px in range(frame_w):
                src = pixels[py * frame_w + px]
                x = origin_x + px
                y = origin_y + py
                pos = (y * sheet_w + x) * 3
                dst = tuple(canvas[pos:pos + 3])
                canvas[pos:pos + 3] = bytes(composite_pixel(dst, src))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_png_rgb(output_path, sheet_w, sheet_h, bytes(canvas))
    raw = output_path.read_bytes()
    if not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw) < 1000:
        raise SystemExit('contact-sheet PNG verification failed')
    print(f'GOLDEN_WEATHER_FRAMES={len(frames)}')
    print(f'GOLDEN_WEATHER_CONTACT_SHEET={output_path}')
    print(f'GOLDEN_WEATHER_SHEET_SIZE={sheet_w}x{sheet_h}')


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: build_weather_contact_sheet.py <Golden-container.bin> <output.png>')
    build(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == '__main__':
    main()
