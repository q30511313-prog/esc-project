#!/usr/bin/env python3
import base64, collections, hashlib, io, re, struct, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile

BASE='https://vas.samsungapps.com/vas/'; PLUGIN='com.samsung.wearable.fit3plugin'; PLUGIN_VERSION='126071051'; SUFFIX='GALAXYAPPSAPI'; UA={'User-Agent':'Mozilla/5.0'}
def get(path,p): return urllib.request.urlopen(urllib.request.Request(BASE+path+'?'+urllib.parse.urlencode(p),headers=UA),timeout=45).read()
def direct(n,t):
    c=n.find(t); return (c.text or '').strip() if c is not None else ''
p={'imgWidth':'216','imgHeight':'432','startNum':'1','endNum':'100','status':'1','cc':'KOR','extraInfo':'screenshot','callerId':PLUGIN,'locale':'ko_KR','alignOrder':'recent','contentCategoryID':'0000004252','mcc':'450','mnc':'10','csc':'NONE','deviceId':'SM-R390','sdkVer':'36','pd':'0'}
r=ET.fromstring(get('product/getContentCategoryProductList.as',p)); face=None
for a in r.findall('appInfo'):
    m=re.search(r'sm_r390_(\d{4,5})$',direct(a,'appId'),re.I)
    if m and m.group(1).zfill(5)=='00003': face=(direct(a,'appId'),direct(a,'versionCode')); break
if not face: raise SystemExit('face not found')
def sh(s): return base64.b64encode(hashlib.sha1((s+SUFFIX).encode('latin1')).digest()).decode()
def stub(s): return {'csc':'NONE','sdkVer':'36','callerId':PLUGIN,'versionCode':PLUGIN_VERSION,'mcc':'450','mnc':'10','systemId':str(int(time.time()*1000)-3600000),'extuk':'0123456789abcdef','abiType':'64','deviceId':'SM-R390','loginType':'N','oneUiVersion':'160000','cc':'KOR','pd':'0','appInfo':s,'hashValue':sh(s)}
d=ET.fromstring(get('stub/gearAppDownload.as',stub(face[0]))); uri=direct(d.find('appInfo'),'downloadURI')
apk=urllib.request.urlopen(urllib.request.Request(uri,headers=UA),timeout=90).read(); z=zipfile.ZipFile(io.BytesIO(apk)); name=[n for n in z.namelist() if n.endswith('SM-R390_00003_256x402.bin')][0]; data=z.read(name)
u16=lambda b,o:struct.unpack_from('<H',b,o)[0]; u32=lambda b,o:struct.unpack_from('<I',b,o)[0]; i16=lambda b,o:struct.unpack_from('<h',b,o)[0]
entries=[]
for i in range(u32(data,12)):
    ro=32+i*74; raw=data[ro:ro+74]; path=raw[:64].split(b'\0',1)[0].decode(); entries.append((path,u32(raw,64),u32(raw,68)))
for path,off,size in entries:
    if not path.endswith('/style0.bin'): continue
    e=data[off:off+size]; imageoff=u32(e,20); cur=24
    print('=== style0 widgets ===')
    while cur<imageoff:
        typ=u32(e,cur); seq=u32(e,cur+4); idxsz=u32(e,cur+12); rs=idxsz&0xffff; gi=idxsz>>16; words=[u32(e,cur+36+j*4) for j in range((rs-36)//4)]
        print(f'g#{gi} type={typ} seq={seq} xy={i16(e,cur+24)},{i16(e,cur+26)} wh={u16(e,cur+28)}x{u16(e,cur+30)} unk20=0x{u32(e,cur+32):08X} words='+' '.join(f'0x{x:08X}' for x in words)); cur+=rs
    imgs=[]; q=imageoff
    while q<len(e):
        w,h,fmt,ds=u16(e,q),u16(e,q+2),u16(e,q+4),u32(e,q+8); rel=q-imageoff; payload=e[q+12:q+12+ds]; imgs.append((rel,w,h,fmt,payload)); q+=12+ds
    rel,w,h,fmt,payload=imgs[0]
    print(f'=== background image#0 rel=0x{rel:08X} {w}x{h} fmt=0x{fmt:04X} ===')
    step=3 if fmt==0x80 else 2
    def pixel(x,y):
        p=(y*w+x)*step; c=struct.unpack_from('<H',payload,p)[0]; a=payload[p+2] if fmt==0x80 else 255
        r=((c>>11)&31)*255//31; g=((c>>5)&63)*255//63; b=(c&31)*255//31
        return r,g,b,a,c
    cnt=collections.Counter()
    for y in range(h):
        for x in range(w):
            r,g,b,a,c=pixel(x,y); cnt[(c,a)]+=1
    print('top565=',[(f'0x{c:04X}',((c>>11&31)*255//31,(c>>5&63)*255//63,(c&31)*255//31),a,n) for (c,a),n in cnt.most_common(16)])
    print('=== long nonblack horizontal runs (>=40 px) ===')
    for y in range(h):
        best=None; start=None
        for x in range(w+1):
            on=False
            if x<w:
                r,g,b,a,c=pixel(x,y); on=a>0 and max(r,g,b)>=12
            if on and start is None: start=x
            if (not on or x==w) and start is not None:
                end=x-1; ln=end-start+1
                if best is None or ln>best[2]: best=(start,end,ln)
                start=None
        if best and best[2]>=40:
            xs=range(best[0],best[1]+1); vals=[pixel(x,y)[:3] for x in xs]; med=tuple(sorted(v[i] for v in vals)[len(vals)//2] for i in range(3))
            print(f'y={y} x={best[0]}..{best[1]} len={best[2]} medianRGB={med}')
