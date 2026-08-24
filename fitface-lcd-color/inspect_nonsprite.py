#!/usr/bin/env python3
import base64, collections, hashlib, io, struct, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile

appid='com.samsung.fit3watchface.sm_r390_0003'; suffix='GALAXYAPPSAPI'
hv=base64.b64encode(hashlib.sha1((appid+suffix).encode('latin1')).digest()).decode()
params={'csc':'NONE','sdkVer':'36','callerId':'com.samsung.wearable.fit3plugin','versionCode':'126071051','mcc':'450','mnc':'10','systemId':str(int(time.time()*1000)),'extuk':'','abiType':'64','deviceId':'SM-R390','loginType':'N','oneUiVersion':'0','cc':'KOR','pd':'0','appInfo':appid,'hashValue':hv}
req=urllib.request.Request('https://vas.samsungapps.com/vas/stub/gearAppDownload.as?'+urllib.parse.urlencode(params),headers={'User-Agent':'Mozilla/5.0'})
root=ET.fromstring(urllib.request.urlopen(req,timeout=30).read())
vals={e.tag:(e.text or '').strip() for e in root.iter()}; dl=vals.get('downloadURI') or vals.get('downloadUri') or vals.get('downloadURL') or vals.get('downloadUrl')
if not dl: raise SystemExit('no download URI')
apk=urllib.request.urlopen(urllib.request.Request(dl,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read()
z=zipfile.ZipFile(io.BytesIO(apk)); members=[n for n in z.namelist() if n.endswith('SM-R390_00003_256x402.bin')]
if len(members)!=1: raise SystemExit(f'container member count {len(members)}')
data=z.read(members[0])
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]; u32=lambda b,o: struct.unpack_from('<I',b,o)[0]; i16=lambda b,o: struct.unpack_from('<h',b,o)[0]
count=u32(data,12); directory=[]
for i in range(count):
    ro=32+i*74; raw=data[ro:ro+74]; path=raw[:64].split(b'\0',1)[0].decode('utf-8','replace'); off=u32(raw,64); size=u32(raw,68); directory.append((path,off,size))
print('=== DIRECTORY ===')
for i,(p,o,s) in enumerate(directory): print(f'{i:02d} {p} off={o} size={s}')
for path,off,size in directory:
    if not path.endswith('style3.bin'): continue
    e=data[off:off+size]; imageoff=u32(e,20); cur=24; recs=[]
    while cur<imageoff:
        typ=u32(e,cur); seq=u32(e,cur+4); idxsz=u32(e,cur+12); rs=idxsz&0xffff; gi=idxsz>>16
        words=[u32(e,cur+36+j*4) for j in range((rs-36)//4)]
        recs.append((cur,typ,seq,gi,i16(e,cur+24),i16(e,cur+26),u16(e,cur+28),u16(e,cur+30),u32(e,cur+32),words)); cur+=rs
    imgs=[]; p=imageoff
    while p<len(e):
        w=u16(e,p); h=u16(e,p+2); fmt=u16(e,p+4); ds=u32(e,p+8); rel=p-imageoff; pix=p+12; payload=e[pix:pix+ds]; imgs.append((rel,w,h,fmt,ds,pix,payload)); p=pix+ds
    imgmap={r:i for i,(r,*_) in enumerate(imgs)}
    print(f'=== STYLE {path} images={len(imgs)} ===')
    for ro,typ,seq,gi,x,y,w,h,unk,words in recs:
        if typ not in (1,5,13): continue
        print(f'WIDGET g#{gi} type={typ} seq={seq} xy={x},{y} wh={w}x{h} unk20=0x{unk:08X} words='+' '.join(f'0x{v:08X}' for v in words))
        if typ==1 and unk in imgmap:
            ii=imgmap[unk]; rel,iw,ih,fmt,ds,pix,payload=imgs[ii]; colors=collections.Counter(); step=3 if fmt==0x80 else 2
            if fmt in (0x80,0x82):
                for q in range(0,min(len(payload),iw*ih*step),step):
                    c=struct.unpack_from('<H',payload,q)[0]; a=payload[q+2] if fmt==0x80 and q+2<len(payload) else 255
                    if a: colors[(c,a)]+=1
            print(f'  STATIC_IMAGE idx={ii} rel={rel} {iw}x{ih} fmt=0x{fmt:04X} top565={colors.most_common(16)}')
print('=== NON_STYLE BIN HEADERS ===')
for path,off,size in directory:
    if path.endswith('.bin') and not any(k in path for k in ('style','preview')):
        blob=data[off:off+size]
        print(f'{path} size={size} head={blob[:128].hex()}')
