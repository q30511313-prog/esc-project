#!/usr/bin/env python3
import base64, collections, hashlib, io, re, struct, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile

BASE='https://vas.samsungapps.com/vas/'
PLUGIN='com.samsung.wearable.fit3plugin'
PLUGIN_VERSION='126071051'
SUFFIX='GALAXYAPPSAPI'
FACE_ID='00003'
UA={'User-Agent':'Mozilla/5.0'}

def get(path, params):
    url=BASE+path+'?'+urllib.parse.urlencode(params)
    return urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=45).read()

def direct(node, tag):
    child=node.find(tag)
    return (child.text or '').strip() if child is not None else ''

catalog_params={'imgWidth':'216','imgHeight':'432','startNum':'1','endNum':'100','status':'1','cc':'KOR','extraInfo':'screenshot','callerId':PLUGIN,'locale':'ko_KR','alignOrder':'recent','contentCategoryID':'0000004252','mcc':'450','mnc':'10','csc':'NONE','deviceId':'SM-R390','sdkVer':'36','pd':'0'}
xml=get('product/getContentCategoryProductList.as',catalog_params); root=ET.fromstring(xml)
face=None
for app in root.findall('appInfo'):
    appid=direct(app,'appId'); m=re.search(r'sm_r390_(\d{4,5})$',appid,re.I)
    if m and m.group(1).zfill(5)==FACE_ID:
        face=(appid,direct(app,'versionCode')); break
if not face: raise SystemExit('face 00003 not found')
appid,version_code=face

def store_hash(app_info): return base64.b64encode(hashlib.sha1((app_info+SUFFIX).encode('latin1')).digest()).decode()
def stub_params(app_info):
    return {'csc':'NONE','sdkVer':'36','callerId':PLUGIN,'versionCode':PLUGIN_VERSION,'mcc':'450','mnc':'10','systemId':str(int(time.time()*1000)-3_600_000),'extuk':'0123456789abcdef','abiType':'64','deviceId':'SM-R390','loginType':'N','oneUiVersion':'160000','cc':'KOR','pd':'0','appInfo':app_info,'hashValue':store_hash(app_info)}

download_xml=get('stub/gearAppDownload.as',stub_params(appid)); droot=ET.fromstring(download_xml); app=droot.find('appInfo'); dl=direct(app,'downloadURI') if app is not None else ''
if not dl: raise SystemExit('download URI missing')
apk=urllib.request.urlopen(urllib.request.Request(dl,headers=UA),timeout=90).read(); z=zipfile.ZipFile(io.BytesIO(apk)); members=[n for n in z.namelist() if n.endswith('SM-R390_00003_256x402.bin')]
if len(members)!=1: raise SystemExit(f'container member count {len(members)}')
data=z.read(members[0])

u16=lambda b,o: struct.unpack_from('<H',b,o)[0]; u32=lambda b,o: struct.unpack_from('<I',b,o)[0]; i16=lambda b,o: struct.unpack_from('<h',b,o)[0]
count=u32(data,12); directory=[]
for i in range(count):
    ro=32+i*74; raw=data[ro:ro+74]; path=raw[:64].split(b'\0',1)[0].decode('utf-8','replace'); off=u32(raw,64); size=u32(raw,68); directory.append((path,off,size))

def rgb565(c):
    r=((c>>11)&31)*255//31; g=((c>>5)&63)*255//63; b=(c&31)*255//31
    return (r,g,b)

def summarize(payload, fmt, w, h):
    step=3 if fmt==0x80 else 2 if fmt==0x82 else 0
    if not step: return 'unsupported'
    colors=collections.Counter(); alphas=collections.Counter()
    limit=min(len(payload),w*h*step)
    for q in range(0,limit,step):
        c=struct.unpack_from('<H',payload,q)[0]
        a=payload[q+2] if fmt==0x80 and q+2<len(payload) else 255
        colors[(c,a)]+=1; alphas[a]+=1
    top=[]
    for (c,a),n in colors.most_common(12):
        top.append((f'0x{c:04X}',rgb565(c),a,n))
    return f'top={top} alpha={alphas.most_common(10)}'

for path,off,size in directory:
    if not path.endswith('/style0.bin'): continue
    e=data[off:off+size]; imageoff=u32(e,20); cur=24; recs=[]
    while cur<imageoff:
        typ=u32(e,cur); seq=u32(e,cur+4); idxsz=u32(e,cur+12); rs=idxsz&0xffff; gi=idxsz>>16
        words=[u32(e,cur+36+j*4) for j in range((rs-36)//4)]
        recs.append((cur,typ,seq,gi,i16(e,cur+24),i16(e,cur+26),u16(e,cur+28),u16(e,cur+30),u32(e,cur+32),words)); cur+=rs
    imgs=[]; p=imageoff
    while p<len(e):
        w=u16(e,p); h=u16(e,p+2); fmt=u16(e,p+4); ds=u32(e,p+8); rel=p-imageoff; pix=p+12; payload=e[pix:pix+ds]; imgs.append((rel,w,h,fmt,ds,payload)); p=pix+ds
    imgmap={rel:(idx,w,h,fmt,ds,payload) for idx,(rel,w,h,fmt,ds,payload) in enumerate(imgs)}
    print('=== style0 clock chrome ===')
    for ro,typ,seq,gi,x,y,w,h,unk,words in recs:
        # Static records at the clock row are the two colons. LineBar records are separator lines/bars.
        if not (typ==17 or (typ==1 and y==166)):
            continue
        ptr = unk if typ==1 else (words[2] if len(words)>2 else None)
        print(f'g#{gi} type={typ} seq={seq} xy={x},{y} wh={w}x{h} unk20=0x{unk:08X} words='+' '.join(f'0x{v:08X}' for v in words))
        if ptr in imgmap:
            idx,iw,ih,fmt,ds,payload=imgmap[ptr]
            print(f'  image#{idx} rel=0x{ptr:08X} {iw}x{ih} fmt=0x{fmt:04X} size={ds} {summarize(payload,fmt,iw,ih)}')
        else:
            print('  raster pointer unresolved:', ptr)
