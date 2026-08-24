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
if direct(root,'resultCode')!='0': print(xml.decode('utf-8','replace')); raise SystemExit('catalog request rejected')
face=None
for app in root.findall('appInfo'):
    appid=direct(app,'appId'); m=re.search(r'sm_r390_(\d{4,5})$',appid,re.I)
    if m and m.group(1).zfill(5)==FACE_ID:
        face=(appid,direct(app,'versionCode'),direct(app,'productName')); break
if not face: raise SystemExit('face 00003 not found')
appid,version_code,name=face
print('CATALOG FACE',FACE_ID,'appId=',appid,'versionCode=',version_code,'name=',name)

def store_hash(app_info): return base64.b64encode(hashlib.sha1((app_info+SUFFIX).encode('latin1')).digest()).decode()
def stub_params(app_info):
    return {'csc':'NONE','sdkVer':'36','callerId':PLUGIN,'versionCode':PLUGIN_VERSION,'mcc':'450','mnc':'10','systemId':str(int(time.time()*1000)-3_600_000),'extuk':'0123456789abcdef','abiType':'64','deviceId':'SM-R390','loginType':'N','oneUiVersion':'160000','cc':'KOR','pd':'0','appInfo':app_info,'hashValue':store_hash(app_info)}
update_xml=get('stub/gearAppUpdateCheck.as',stub_params(f'{appid}@{version_code}'))
print('UPDATE OK', b'<resultCode>0</resultCode>' in update_xml)
download_xml=get('stub/gearAppDownload.as',stub_params(appid)); droot=ET.fromstring(download_xml); app=droot.find('appInfo'); dl=direct(app,'downloadURI') if app is not None else ''; result=direct(app,'resultCode') if app is not None else ''
if result!='1' or not dl: print(download_xml.decode('utf-8','replace')); raise SystemExit(0)
apk=urllib.request.urlopen(urllib.request.Request(dl,headers=UA),timeout=90).read(); z=zipfile.ZipFile(io.BytesIO(apk)); members=[n for n in z.namelist() if n.endswith('SM-R390_00003_256x402.bin')]
if len(members)!=1: raise SystemExit(f'container member count {len(members)}')
data=z.read(members[0]); print('CONTAINER BYTES',len(data),'SHA256',hashlib.sha256(data).hexdigest())
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]; u32=lambda b,o: struct.unpack_from('<I',b,o)[0]; i16=lambda b,o: struct.unpack_from('<h',b,o)[0]
count=u32(data,12); directory=[]
for i in range(count):
    ro=32+i*74; raw=data[ro:ro+74]; path=raw[:64].split(b'\0',1)[0].decode('utf-8','replace'); off=u32(raw,64); size=u32(raw,68); directory.append((path,off,size))

for path,off,size in directory:
    if not re.search(r'/style\d+\.bin$',path): continue
    e=data[off:off+size]; imageoff=u32(e,20); cur=24; recs=[]
    while cur<imageoff:
        typ=u32(e,cur); seq=u32(e,cur+4); idxsz=u32(e,cur+12); rs=idxsz&0xffff; gi=idxsz>>16
        words=[u32(e,cur+36+j*4) for j in range((rs-36)//4)]
        recs.append((cur,typ,seq,gi,i16(e,cur+24),i16(e,cur+26),u16(e,cur+28),u16(e,cur+30),u32(e,cur+32),words)); cur+=rs
    imgs=[]; p=imageoff
    while p<len(e):
        w=u16(e,p); h=u16(e,p+2); fmt=u16(e,p+4); ds=u32(e,p+8); rel=p-imageoff; pix=p+12; payload=e[pix:pix+ds]; imgs.append((rel,w,h,fmt,ds,pix,payload)); p=pix+ds
    imgmap={r:i for i,(r,*_) in enumerate(imgs)}
    print(f'=== {path.rsplit("/",1)[-1]} images={len(imgs)} ===')
    for ro,typ,seq,gi,x,y,w,h,unk,words in recs:
        if typ not in (1,5,13): continue
        extra=''
        if typ==5:
            extra=f' PAIR_COLOR@+24=0x{words[0]:08X}' if words else ''
        elif typ==13:
            extra=f' COMP_COLOR@+58=0x{words[13]:08X}' if len(words)>13 else ' COMP_NO_WORD13'
        print(f'g#{gi} type={typ} seq={seq} rec={36+len(words)*4} xy={x},{y} wh={w}x{h} unk20=0x{unk:08X}{extra} words='+' '.join(f'0x{v:08X}' for v in words))
        if typ==1 and unk in imgmap and gi in (5,8):
            ii=imgmap[unk]; rel,iw,ih,fmt,ds,pix,payload=imgs[ii]; colors=collections.Counter(); step=3 if fmt==0x80 else 2
            if fmt in (0x80,0x82):
                for q in range(0,min(len(payload),iw*ih*step),step):
                    c=struct.unpack_from('<H',payload,q)[0]; a=payload[q+2] if fmt==0x80 and q+2<len(payload) else 255
                    if a: colors[(c,a)]+=1
            print(f'  STATIC_IMAGE idx={ii} rel={rel} {iw}x{ih} fmt=0x{fmt:04X} top565={colors.most_common(8)}')

print('=== FONT BINDINGS ===')
for path,off,size in directory:
    if re.search(r'/font_\d+\.bin$',path):
        blob=data[off:off+size]; role=blob[0x48:0x58].split(b'\0',1)[0].decode('ascii','replace'); family=blob[0]; pt=u32(blob,0x58)
        print(path.rsplit('/',1)[-1], 'role=',role,'family=',family,'pt=',pt,'head=',blob[:72].hex())
