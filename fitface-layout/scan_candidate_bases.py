#!/usr/bin/env python3
import base64
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

OUT = pathlib.Path('out_candidates')
OUT.mkdir(exist_ok=True)
CANDIDATES = {
    '00049', '00011', '00010', '00009', '00007', '00006',
    '00028', '00102', '00105', '00106', '00066', '00008',
}


def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def s16(b, o): return struct.unpack_from('<h', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=timeout).read()


def catalog():
    params = {
        'imgWidth':'216','imgHeight':'432','startNum':'1','endNum':'100','status':'1',
        'cc':'KOR','extraInfo':'screenshot','callerId':'com.samsung.wearable.fit3plugin',
        'locale':'en_US','alignOrder':'recent','contentCategoryID':'0000004252',
        'mcc':'450','mnc':'10','csc':'NONE','deviceId':'SM-R390','sdkVer':'36','pd':'0',
    }
    url='https://vas.samsungapps.com/vas/product/getContentCategoryProductList.as?'+urllib.parse.urlencode(params)
    root=ET.fromstring(get(url,30))
    result=[]
    for app in root.findall('appInfo'):
        appid=(app.findtext('appId') or '').strip()
        m=re.search(r'sm_r390_(\d{4,5})$',appid,re.I)
        if not m: continue
        face=m.group(1).zfill(5)
        if face not in CANDIDATES: continue
        result.append({
            'face':face,
            'name':(app.findtext('productName') or '').strip(),
            'appId':appid,
            'versionCode':(app.findtext('versionCode') or '').strip(),
        })
    return result


def store_download(face):
    appid=face['appId']
    hv=base64.b64encode(hashlib.sha1((appid+'GALAXYAPPSAPI').encode('latin1')).digest()).decode()
    params={
        'csc':'NONE','sdkVer':'36','callerId':'com.samsung.wearable.fit3plugin',
        'versionCode':'126071051','mcc':'450','mnc':'10',
        'systemId':str(int(time.time()*1000)-86400000),
        'extuk':'0123456789abcdef','abiType':'64','deviceId':'SM-R390',
        'loginType':'N','oneUiVersion':'0','cc':'KOR','pd':'0',
        'appInfo':appid,'hashValue':hv,
    }
    url='https://vas.samsungapps.com/vas/stub/gearAppDownload.as?'+urllib.parse.urlencode(params)
    root=ET.fromstring(get(url,30))
    app=next((e for e in root.iter() if e.tag=='appInfo'),None)
    vals={e.tag:(e.text or '').strip() for e in app.iter()} if app is not None else {}
    if vals.get('resultCode')!='1' or not vals.get('downloadURI'):
        raise RuntimeError(f"{face['face']} download result {vals}")
    return get(vals['downloadURI'],60), vals


def directory(data):
    out=[]
    for i in range(u32(data,12)):
        ro=32+i*74; raw=data[ro:ro+74]
        path=raw[:64].split(b'\0',1)[0].decode('utf-8','replace')
        off=u32(raw,64); size=u32(raw,68)
        out.append((path,data[off:off+size]))
    return out


def ko_groups(entries):
    for path,blob in entries:
        if pathlib.Path(path).name!='font_ko.bin' or len(blob)<24: continue
        n=u32(blob,8); result=[]
        for g in range(n):
            ln=u32(blob,0x18+g*8); rel=u32(blob,0x1c+g*8)
            result.append(blob[rel:rel+ln].decode('utf-8','replace'))
        return result
    return []


def font_roles(entries):
    roles=[]
    for path,blob in entries:
        name=pathlib.Path(path).name
        if name.startswith('font_') and len(blob)==92:
            roles.append({
                'file':name,'family':blob[0],
                'role':blob[0x48:0x58].split(b'\0',1)[0].decode('ascii','replace'),
                'pointSize':u32(blob,0x58),
            })
    return roles


def scan_style(name, entry):
    imageoff=u32(entry,20); cur=24; records=[]
    while cur<imageoff:
        typ=u32(entry,cur); seq=u32(entry,cur+4); idxsz=u32(entry,cur+12)
        size=idxsz&0xffff; gi=idxsz>>16
        x=s16(entry,cur+0x18); y=s16(entry,cur+0x1a)
        w=s16(entry,cur+0x1c); h=s16(entry,cur+0x1e)
        words=[u32(entry,cur+36+j*4) for j in range((size-36)//4)]
        records.append({'g':gi,'type':typ,'seq':seq,'x':x,'y':y,'w':w,'h':h,'size':size,'words':words})
        cur+=size
    return {'style':name,'records':records}


def extract_previews(z, faceid):
    saved=[]
    needle=f'SM-R390_{faceid}_'.lower()
    for name in z.namelist():
        low=name.lower()
        if not low.endswith('.png') or needle not in low: continue
        if '/ko_kr/' not in low: continue
        payload=z.read(name)
        target=OUT/f'{faceid}_{pathlib.Path(name).name}'
        target.write_bytes(payload)
        saved.append(target.name)
    return saved


def main():
    summary=[]
    faces=catalog()
    print('CANDIDATES',[(f['face'],f['name']) for f in faces])
    for face in faces:
        fid=face['face']
        try:
            apk,meta=store_download(face)
            z=zipfile.ZipFile(io.BytesIO(apk))
            members=[n for n in z.namelist() if n.endswith(f'SM-R390_{fid}_256x402.bin')]
            if len(members)!=1:
                raise RuntimeError(f'container count={len(members)}')
            data=z.read(members[0]); entries=directory(data)
            styles=[]
            for path,blob in entries:
                bn=pathlib.Path(path).name
                if re.fullmatch(r'style\d+\.bin',bn):
                    styles.append(scan_style(bn,blob))
            item={
                'face':fid,'name':face['name'],'appId':face['appId'],
                'storeVersion':meta.get('versionName'),'containerBytes':len(data),
                'koGroups':ko_groups(entries),'fontRoles':font_roles(entries),
                'styles':styles,'previewFiles':extract_previews(z,fid),
            }
            summary.append(item)
            print('OK',fid,face['name'],'styles',len(styles),'koGroups',item['koGroups'])
            for style in styles:
                seqs=[(r['type'],r['seq'],r['x'],r['y']) for r in style['records']]
                print(' ',style['style'],seqs)
        except Exception as exc:
            summary.append({'face':fid,'name':face['name'],'error':repr(exc)})
            print('FAIL',fid,face['name'],repr(exc))
    (OUT/'candidate_semantics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
