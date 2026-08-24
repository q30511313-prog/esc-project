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

# 1) Resolve the exact current appId/versionCode from the public Fit3 catalogue.
catalog_params={
    'imgWidth':'216','imgHeight':'432','startNum':'1','endNum':'100','status':'1',
    'cc':'KOR','extraInfo':'screenshot','callerId':PLUGIN,'locale':'ko_KR',
    'alignOrder':'recent','contentCategoryID':'0000004252','mcc':'450','mnc':'10',
    'csc':'NONE','deviceId':'SM-R390','sdkVer':'36','pd':'0',
}
xml=get('product/getContentCategoryProductList.as',catalog_params)
root=ET.fromstring(xml)
if direct(root,'resultCode')!='0':
    print(xml.decode('utf-8','replace')); raise SystemExit('catalog request rejected')
face=None
for app in root.findall('appInfo'):
    appid=direct(app,'appId')
    m=re.search(r'sm_r390_(\d{4,5})$', appid, re.I)
    if m and m.group(1).zfill(5)==FACE_ID:
        face=(appid,direct(app,'versionCode'),direct(app,'productName'))
        break
if not face:
    print(xml.decode('utf-8','replace')); raise SystemExit('face 00003 not found in first catalogue page')
appid,version_code,name=face
print('CATALOG FACE',FACE_ID,'appId=',appid,'versionCode=',version_code,'name=',name)

def store_hash(app_info):
    return base64.b64encode(hashlib.sha1((app_info+SUFFIX).encode('latin1')).digest()).decode()

def stub_params(app_info):
    # Android implementation sends estimated boot epoch, not current wall time.
    boot_epoch_ms=int(time.time()*1000)-3_600_000
    return {
        'csc':'NONE','sdkVer':'36','callerId':PLUGIN,'versionCode':PLUGIN_VERSION,
        'mcc':'450','mnc':'10','systemId':str(boot_epoch_ms),
        'extuk':'0123456789abcdef','abiType':'64','deviceId':'SM-R390','loginType':'N',
        'oneUiVersion':'160000','cc':'KOR','pd':'0','appInfo':app_info,
        'hashValue':store_hash(app_info),
    }

# 2) Same update-check handshake the app performs before asking for a package.
update_info=f'{appid}@{version_code}'
update_xml=get('stub/gearAppUpdateCheck.as',stub_params(update_info))
print('UPDATE RESPONSE',update_xml.decode('utf-8','replace')[:1200])

# 3) Request the signed download URI for the exact catalog appId.
download_xml=get('stub/gearAppDownload.as',stub_params(appid))
droot=ET.fromstring(download_xml)
app=droot.find('appInfo')
dl=direct(app,'downloadURI') if app is not None else ''
result=direct(app,'resultCode') if app is not None else ''
if result!='1' or not dl:
    print('=== SAMSUNG DOWNLOAD RESPONSE WITHOUT URI ===')
    print(download_xml.decode('utf-8','replace'))
    raise SystemExit(0)
print('DOWNLOAD URI HOST',urllib.parse.urlparse(dl).netloc)
apk=urllib.request.urlopen(urllib.request.Request(dl,headers=UA),timeout=90).read()
z=zipfile.ZipFile(io.BytesIO(apk)); members=[n for n in z.namelist() if n.endswith('SM-R390_00003_256x402.bin')]
if len(members)!=1: raise SystemExit(f'container member count {len(members)}')
data=z.read(members[0])
print('CONTAINER BYTES',len(data),'SHA256',hashlib.sha256(data).hexdigest())

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
        print(f'WIDGET g#{gi} type={typ} seq={seq} rec={36+len(words)*4} xy={x},{y} wh={w}x{h} unk20=0x{unk:08X} words='+' '.join(f'0x{v:08X}' for v in words))
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
