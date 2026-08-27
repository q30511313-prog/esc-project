#!/usr/bin/env python3
"""Find stock Fit3 faces that expose live weather seq69 plus Korean locale strings."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import io
import json
import pathlib
import re
import struct
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

STORE = 'https://vas.samsungapps.com/vas/'
UA = {'User-Agent': 'Mozilla/5.0'}


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def get(url, timeout=60, limit=32 * 1024 * 1024):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError('response too large')
    return data


def catalog():
    params = {
        'imgWidth':'216','imgHeight':'432','startNum':'1','endNum':'100','status':'1',
        'cc':'KOR','extraInfo':'screenshot','callerId':'com.samsung.wearable.fit3plugin',
        'locale':'ko_KR','alignOrder':'recent','contentCategoryID':'0000004252','mcc':'450',
        'mnc':'10','csc':'NONE','deviceId':'SM-R390','sdkVer':'36','pd':'0'
    }
    root = ET.fromstring(get(STORE + 'product/getContentCategoryProductList.as?' + urllib.parse.urlencode(params), 30, 1024 * 1024))
    result = []
    for app in root.findall('appInfo'):
        app_id = (app.findtext('appId') or '').strip()
        match = re.search(r'sm_r390_(\d{4,5})$', app_id, re.I)
        if not match:
            continue
        result.append({
            'face': match.group(1).zfill(5),
            'appId': app_id,
            'name': (app.findtext('productName') or '').strip(),
        })
    return result


def download(face):
    app_id = face['appId']
    hv = base64.b64encode(hashlib.sha1((app_id + 'GALAXYAPPSAPI').encode('latin1')).digest()).decode()
    params = {
        'csc':'NONE','sdkVer':'36','callerId':'com.samsung.wearable.fit3plugin',
        'versionCode':'126071051','mcc':'450','mnc':'10',
        'systemId':str(int(time.time()*1000)-86400000),'extuk':'0123456789abcdef',
        'abiType':'64','deviceId':'SM-R390','loginType':'N','oneUiVersion':'0',
        'cc':'KOR','pd':'0','appInfo':app_id,'hashValue':hv,
    }
    root = ET.fromstring(get(STORE + 'stub/gearAppDownload.as?' + urllib.parse.urlencode(params), 30, 512 * 1024))
    app = next((node for node in root.iter() if node.tag == 'appInfo'), None)
    values = {node.tag:(node.text or '').strip() for node in app.iter()} if app is not None else {}
    if values.get('resultCode') != '1' or not values.get('downloadURI'):
        raise RuntimeError(f"download result={values.get('resultCode')} {values.get('resultMsg')}")
    package = get(values['downloadURI'], 60)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        members = [name for name in archive.namelist() if name.endswith(f"SM-R390_{face['face']}_256x402.bin")]
        if len(members) != 1:
            raise RuntimeError(f'container count={len(members)}')
        return archive.read(members[0])


def directory(container):
    out = []
    for index in range(u32(container, 12)):
        record = 32 + index * 74
        raw = container[record:record+74]
        path = raw[:64].split(b'\0', 1)[0].decode('utf-8', 'replace')
        offset = u32(raw, 64)
        size = u32(raw, 68)
        out.append((path, container[offset:offset+size]))
    return out


def locale_groups(entries):
    for path, data in entries:
        if pathlib.Path(path).name == 'font_ko.bin' and len(data) >= 24:
            count = u32(data, 8)
            groups = []
            for index in range(count):
                length = u32(data, 0x18 + index * 8)
                offset = u32(data, 0x1C + index * 8)
                if offset + length > len(data):
                    raise RuntimeError('locale group out of bounds')
                groups.append(data[offset:offset+length].decode('utf-8', 'replace'))
            return groups
    return []


def font_roles(entries):
    roles = []
    for path, data in entries:
        name = pathlib.Path(path).name
        if name.startswith('font_') and len(data) == 92:
            role = data[0x48:0x58].split(b'\0', 1)[0].decode('ascii', 'replace')
            roles.append(role)
    return roles


def scan_widgets(style):
    image_offset = u32(style, 20)
    cursor = 24
    records = []
    while cursor < image_offset:
        widget_type = u32(style, cursor)
        sequence = u32(style, cursor + 4)
        index_size = u32(style, cursor + 12)
        record_size = index_size & 0xFFFF
        global_index = index_size >> 16
        words = [u32(style, cursor + 36 + i * 4) for i in range((record_size - 36)//4)]
        records.append({'g':global_index,'type':widget_type,'seq':sequence,'words':words})
        cursor += record_size
    return records


def analyze(face):
    try:
        container = download(face)
        entries = directory(container)
        groups = locale_groups(entries)
        roles = font_roles(entries)
        styles = []
        has_weather = False
        for path, data in entries:
            name = pathlib.Path(path).name
            if not re.fullmatch(r'style\d+\.bin', name):
                continue
            records = scan_widgets(data)
            weather = [record for record in records if record['type'] == 3 and record['seq'] == 69]
            if weather:
                has_weather = True
                textish = [record for record in records if record['type'] in (5,13)]
                styles.append({
                    'style': name,
                    'weather': weather,
                    'pairComposite': textish,
                    'topSequences': sorted(set(record['seq'] for record in records)),
                })
        if not has_weather:
            return None
        korean = [group for group in groups if re.search(r'[가-힣]', group)]
        return {
            'face': face['face'],
            'name': face['name'],
            'localeGroups': groups,
            'koreanGroups': korean,
            'fontRoles': roles,
            'styles': styles,
        }
    except Exception as error:
        return {'face':face['face'],'name':face['name'],'error':repr(error)}


def main():
    faces = catalog()
    print(f'CATALOG_FACE_COUNT={len(faces)}')
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(analyze, face): face for face in faces}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
    results.sort(key=lambda item: item['face'])
    good = [item for item in results if 'error' not in item]
    print(f'WEATHER_SEQ69_FACE_COUNT={len(good)}')
    for item in results:
        print('WEATHER_LOCALE_CANDIDATE_JSON=' + json.dumps(item, ensure_ascii=False, separators=(',',':')))


if __name__ == '__main__':
    main()
