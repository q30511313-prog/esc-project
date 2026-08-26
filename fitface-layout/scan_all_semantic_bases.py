#!/usr/bin/env python3
import base64, hashlib, io, json, pathlib, re, struct, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
import zipfile

OUT=pathlib.Path('out_all_bases'); OUT.mkdir(exist_ok=True)
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def s16(b,o): return struct.unpack_from('<h',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def get(url,timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=timeout).read()

def fetch_catalog():
    params={'imgWidth':'216','imgHeight':'432','startNum':'1','endNum':'100','status':'1','cc':'KOR','extraInfo':'screenshot','callerId':'com.samsung.wearable.fit3plugin','locale':'en_US','alignOrder':'recent','contentCategoryID':'0000004252','mcc':'450','mnc':'10','csc':'NONE','deviceId':'SM-R390','sdkVer':'36','pd':'0'}
    root=ET.fromstring(get('https://vas.samsungapps.com/vas/product/getContentCategoryProductList.as?'+urllib.parse.urlencode(params),30))
    faces=[]
    for app in root.findall('appInfo'):
        aid=(app.findtext('appId') or '').strip(); m=re.search(r'sm_r390_(\d{4,5})$',aid,re.I)
        if not m: continue
        faces.append({'face':m.group(1).zfill(5),'name':(app.findtext('productName') or '').strip(),'appId':aid})
    return faces

def download(face):
    aid=face['appId']; hv=base64.b64encode(hashlib.sha1((aid+'GALAXYAPPSAPI').encode('latin1')).digest()).decode()
    params={'csc':'NONE','sdkVer':'36','callerId':'com.samsung.wearable.fit3plugin','versionCode':'126071051','mcc':'450','mnc':'10','systemId':str(int(time.time()*1000)-86400000),'extuk':'0123456789abcdef','abiType':'64','deviceId':'SM-R390','loginType':'N','oneUiVersion':'0','cc':'KOR','pd':'0','appInfo':aid,'hashValue':hv}
    root=ET.fromstring(get('https://vas.samsungapps.com/vas/stub/gearAppDownload.as?'+urllib.parse.urlencode(params),30))
    app=next((e for e in root.iter() if e.tag=='appInfo'),None); vals={e.tag:(e.text or '').strip() for e in app.iter()} if app is not None else {}
    if vals.get('resultCode')!='1' or not vals.get('downloadURI'): raise RuntimeError(f"download result={vals.get('resultCode')} {vals.get('resultMsg')}")
    return get(vals['downloadURI'],60)

def directory(data):
    out=[]
    for i in range(u32(data,12)):
        ro=32+i*74; raw=data[ro:ro+74]; path=raw[:64].split(b'\0',1)[0].decode('utf-8','replace'); off=u32(raw,64); size=u32(raw,68)
        out.append((path,data[off:off+size]))
    return out

def scan_records(entry):
    imageoff=u32(entry,20); cur=24; rec=[]
    while cur<imageoff:
        typ=u32(entry,cur); seq=u32(entry,cur+4); idxsz=u32(entry,cur+12); rs=idxsz&0xffff
        words=[u32(entry,cur+36+j*4) for j in range((rs-36)//4)]
        rec.append({'type':typ,'seq':seq,'x':s16(entry,cur+24),'y':s16(entry,cur+26),'w':s16(entry,cur+28),'h':s16(entry,cur+30),'words':words})
        cur+=rs
    return rec

def groups(entries):
    for p,b in entries:
        if pathlib.Path(p).name=='font_ko.bin' and len(b)>=24:
            n=u32(b,8); out=[]
            for g in range(n):
                ln=u32(b,0x18+g*8); rel=u32(b,0x1c+g*8); out.append(b[rel:rel+ln].decode('utf-8','replace'))
            return out
    return []

def roles(entries):
    out=[]
    for p,b in entries:
        if pathlib.Path(p).name.startswith('font_') and len(b)==92:
            out.append(b[0x48:0x58].split(b'\0',1)[0].decode('ascii','replace'))
    return out

def comp_inner_sequences(records):
    seqs=set()
    for r in records:
        if r['type']!=13: continue
        for word in r['words'][:12]:
            lo=word&0xffff
            if lo not in (0,0xffff): seqs.add(lo)
    return sorted(seqs)

def score(style, ko):
    top={r['seq'] for r in style}
    inner=set(comp_inner_sequences(style))
    # Proven/strongly observed semantic ids across the stock corpus:
    # 2/3 hour, 10/11 minute, 14/15 second, 5 AM/PM, 17 weekday,
    # 37 battery, 69 weather icon, 62 temperature; date commonly uses 18/21 plus separators.
    checks={
        'hourMinute': {2,3,10,11}.issubset(top),
        'seconds': {14,15}.issubset(top),
        'amPm': 5 in top,
        'weekday': 17 in top or any(x in ''.join(ko) for x in ['월요일','(월)']),
        'battery': 37 in top or 37 in inner,
        'weatherIcon': 69 in top,
        'temperature': 62 in top or 62 in inner,
        'dateNumeric': bool(({18,21}&inner) or ({18,21}&top)),
        'yearCandidate': 17 in inner,
    }
    return checks, sum(checks.values())

def main():
    results=[]; faces=fetch_catalog(); print('faces',len(faces))
    for idx,face in enumerate(faces,1):
        try:
            apk=download(face); z=zipfile.ZipFile(io.BytesIO(apk)); fid=face['face']
            mem=[n for n in z.namelist() if n.endswith(f'SM-R390_{fid}_256x402.bin')]
            if len(mem)!=1: raise RuntimeError(f'container count={len(mem)}')
            data=z.read(mem[0]); entries=directory(data); ko=groups(entries); role=roles(entries)
            best=None; styles=[]
            for p,b in entries:
                bn=pathlib.Path(p).name
                if not re.fullmatch(r'style\d+\.bin',bn): continue
                rec=scan_records(b); checks,sc=score(rec,ko)
                item={'style':bn,'score':sc,'checks':checks,'topSequences':sorted({r['seq'] for r in rec}),'innerSequences':comp_inner_sequences(rec),'recordCount':len(rec)}
                styles.append(item)
                if best is None or sc>best['score']: best=item
            res={'face':fid,'name':face['name'],'koGroups':ko,'fontRoles':role,'best':best,'styles':styles}
            results.append(res)
            print(f"{idx:03d}/{len(faces)} {fid} {face['name']} score={best['score'] if best else -1} {best['checks'] if best else {}}")
        except Exception as e:
            results.append({'face':face['face'],'name':face['name'],'error':repr(e)})
            print(f"{idx:03d}/{len(faces)} {face['face']} FAIL {e!r}")
    results.sort(key=lambda x: (-(x.get('best') or {}).get('score',-1), x['face']))
    (OUT/'all_base_semantics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    with (OUT/'ranking.txt').open('w') as f:
        for r in results:
            if 'error' in r: f.write(f"ERR {r['face']} {r['name']} {r['error']}\n"); continue
            b=r['best']; f.write(f"{b['score']} {r['face']} {r['name']} {json.dumps(b['checks'],ensure_ascii=False)} top={b['topSequences']} inner={b['innerSequences']}\n")

if __name__=='__main__': main()
