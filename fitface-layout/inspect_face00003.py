#!/usr/bin/env python3
import base64
import hashlib
import io
import json
import pathlib
import struct
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

OUT = pathlib.Path('out')
OUT.mkdir(exist_ok=True)

APP_ID = 'com.samsung.fit3watchface.sm_r390_0003'
HASH_SUFFIX = 'GALAXYAPPSAPI'


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def s16(b, o):
    return struct.unpack_from('<h', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def download_stock_apk():
    hv = base64.b64encode(
        hashlib.sha1((APP_ID + HASH_SUFFIX).encode('latin1')).digest()
    ).decode()
    params = {
        'csc': 'NONE',
        'sdkVer': '36',
        'callerId': 'com.samsung.wearable.fit3plugin',
        'versionCode': '126071051',
        'mcc': '450',
        'mnc': '10',
        # The stock app sends the phone boot epoch, not wall-clock now.
        'systemId': str(int(time.time() * 1000) - 86400000),
        # Current Samsung endpoint rejects an empty extuk as a missing mandatory field.
        # Use a stable synthetic Android-ID-shaped value for read-only inspection.
        'extuk': '0123456789abcdef',
        'abiType': '64',
        'deviceId': 'SM-R390',
        'loginType': 'N',
        'oneUiVersion': '0',
        'cc': 'KOR',
        'pd': '0',
        'appInfo': APP_ID,
        'hashValue': hv,
    }
    stub = 'https://vas.samsungapps.com/vas/stub/gearAppDownload.as?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(stub, headers={'User-Agent': 'Mozilla/5.0'})
    xml = urllib.request.urlopen(req, timeout=30).read()
    (OUT / 'download.xml').write_bytes(xml)
    root = ET.fromstring(xml)
    app = next((e for e in root.iter() if e.tag == 'appInfo'), None)
    if app is None:
        raise SystemExit(xml.decode('utf-8', 'replace'))
    vals = {e.tag: (e.text or '').strip() for e in app.iter()}
    if vals.get('resultCode') != '1' or not vals.get('downloadURI'):
        raise SystemExit(xml.decode('utf-8', 'replace'))
    dl = vals['downloadURI']
    req = urllib.request.Request(dl, headers={'User-Agent': 'Mozilla/5.0'})
    apk = urllib.request.urlopen(req, timeout=60).read()
    (OUT / 'face00003.apk').write_bytes(apk)
    print('STORE_PRODUCT', vals.get('productName', ''))
    print('STORE_VERSION', vals.get('versionName', ''), vals.get('versionCode', ''))
    print('APK_BYTES', len(apk))
    print('APK_SHA256', hashlib.sha256(apk).hexdigest())
    return apk


def parse_directory(data):
    entries = []
    count = u32(data, 12)
    for i in range(count):
        ro = 32 + i * 74
        raw = data[ro:ro + 74]
        path = raw[:64].split(b'\0', 1)[0].decode('utf-8', 'replace')
        off = u32(raw, 64)
        size = u32(raw, 68)
        entries.append((i, path, off, size, data[off:off + size]))
    return entries


def scan_images(entry, image_section):
    images = {}
    cur = image_section
    while cur < len(entry):
        if cur + 12 > len(entry):
            break
        w = u16(entry, cur)
        h = u16(entry, cur + 2)
        fmt = u16(entry, cur + 4)
        dsize = u32(entry, cur + 8)
        end = cur + 12 + dsize
        if w <= 0 or h <= 0 or dsize < 4 or end > len(entry):
            break
        images[cur - image_section] = {
            'w': w,
            'h': h,
            'format': fmt,
            'dataSize': dsize,
            'recordSize': 12 + dsize,
        }
        cur = end
    return images


def save_apk_previews(z):
    candidates = []
    for name in z.namelist():
        low = name.lower()
        if not low.endswith(('.png', '.jpg', '.jpeg')):
            continue
        if 'sm-r390_00003' in low or 'sm_r390_0003' in low or 'sm_r390_00003' in low:
            candidates.append(name)
    lines = []
    for index, name in enumerate(candidates):
        payload = z.read(name)
        suffix = pathlib.Path(name).suffix.lower() or '.bin'
        target = OUT / f'preview_asset_{index:02d}{suffix}'
        target.write_bytes(payload)
        lines.append(f'{index:02d}\t{name}\t{len(payload)}\t{target.name}')
    (OUT / 'preview_assets.txt').write_text('\n'.join(lines) + ('\n' if lines else ''))
    print('PREVIEW_ASSETS', len(lines))


def dump_font_roles(entries):
    lines = []
    for _, path, _, _, entry in entries:
        name = pathlib.Path(path).name
        if name.startswith('font_') and len(entry) == 92:
            family = entry[0]
            role = entry[0x48:0x58].split(b'\0', 1)[0].decode('ascii', 'replace')
            point_size = u32(entry, 0x58)
            lines.append(f'{name}: family={family} role={role} pointSize={point_size}')
    (OUT / 'font_roles.txt').write_text('\n'.join(lines) + '\n')
    print('FONT_ROLES')
    print('\n'.join(lines))


def dump_korean_glyph_groups(entries):
    lines = []
    for _, path, _, _, entry in entries:
        name = pathlib.Path(path).name
        if name != 'font_ko.bin' or len(entry) < 24:
            continue
        magic = u32(entry, 0)
        locale_id = u32(entry, 4)
        group_count = u32(entry, 8)
        lines.append(f'{name}: magic=0x{magic:08X} locale={locale_id} groups={group_count}')
        for group in range(group_count):
            length = u32(entry, 0x18 + group * 8)
            rel = u32(entry, 0x1C + group * 8)
            text = entry[rel:rel + length].decode('utf-8', 'replace')
            lines.append(f'group[{group}] len={length} off={rel} text={text!r}')
    (OUT / 'font_ko_groups.txt').write_text('\n'.join(lines) + '\n')
    print('KOREAN_GLYPH_GROUPS')
    print('\n'.join(lines))


def dump_style3(entries):
    report = []
    inventory = []
    for _, path, _, _, entry in entries:
        if not path.endswith('style3.bin'):
            continue
        widget_count = u32(entry, 4)
        image_offset = u32(entry, 20)
        images = scan_images(entry, image_offset)
        report.append(f'ENTRY {path} widgets={widget_count} imageoff={image_offset} images={len(images)}')
        cur = 24
        ordinal = 0
        while cur < image_offset:
            typ = u32(entry, cur)
            seq = u32(entry, cur + 4)
            idx_size = u32(entry, cur + 12)
            record_size = idx_size & 0xFFFF
            global_index = idx_size >> 16
            x = s16(entry, cur + 0x18)
            y = s16(entry, cur + 0x1A)
            w_field = s16(entry, cur + 0x1C)
            h_field = s16(entry, cur + 0x1E)
            words = [u32(entry, cur + 36 + j * 4) for j in range((record_size - 36) // 4)]

            frame_info = []
            if typ == 1 and words:
                image = images.get(words[0])
                if image:
                    frame_info.append({'offset': words[0], **image})
            elif typ == 3 and words:
                frame_count = words[0]
                for pointer in words[1:1 + frame_count]:
                    image = images.get(pointer)
                    if image:
                        frame_info.append({'offset': pointer, **image})
            elif typ == 2 and len(words) >= 2:
                image = images.get(words[1])
                if image:
                    frame_info.append({'offset': words[1], **image})

            sizes = sorted({(f['w'], f['h'], f['format']) for f in frame_info})
            report.append(
                f'W#{ordinal:02d} g#{global_index:02d} type={typ:02d} seq={seq:03d} '
                f'xy=({x:4d},{y:4d}) fieldWH=({w_field:4d},{h_field:4d}) '
                f'size={record_size:3d} frames={len(frame_info):2d} frameSizes={sizes} '
                'words=' + ','.join(f'0x{word:08X}' for word in words)
            )
            inventory.append({
                'ordinal': ordinal,
                'globalIndex': global_index,
                'type': typ,
                'sequenceId': seq,
                'x': x,
                'y': y,
                'widthField': w_field,
                'heightField': h_field,
                'recordSize': record_size,
                'words': words,
                'frameInfo': frame_info,
            })
            ordinal += 1
            cur += record_size
        if ordinal != widget_count:
            raise SystemExit(f'widget count mismatch parsed={ordinal} header={widget_count}')

    (OUT / 'style3_widget_inventory.txt').write_text('\n'.join(report) + '\n')
    (OUT / 'style3_widget_inventory.json').write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2)
    )
    print('STYLE3_WIDGET_INVENTORY')
    print('\n'.join(report))


def main():
    apk = download_stock_apk()
    z = zipfile.ZipFile(io.BytesIO(apk))
    members = [name for name in z.namelist() if name.endswith('SM-R390_00003_256x402.bin')]
    if len(members) != 1:
        raise SystemExit(f'container member not unique: {members}')
    data = z.read(members[0])
    (OUT / 'SM-R390_00003_256x402.bin').write_bytes(data)
    print('CONTAINER_MEMBER', members[0])
    print('CONTAINER_BYTES', len(data))
    print('CONTAINER_SHA256', hashlib.sha256(data).hexdigest())

    save_apk_previews(z)
    entries = parse_directory(data)
    dump_font_roles(entries)
    dump_korean_glyph_groups(entries)
    dump_style3(entries)


if __name__ == '__main__':
    main()
