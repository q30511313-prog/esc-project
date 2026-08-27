#!/usr/bin/env python3
import json
import pathlib
import struct
import sys


def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]


def main():
    c=pathlib.Path(sys.argv[1]).read_bytes()
    entries={}
    for i in range(u32(c,12)):
        r=32+i*74
        name=pathlib.Path(c[r:r+64].split(b'\0',1)[0].decode()).name
        off=u32(c,r+64); size=u32(c,r+68)
        entries[name]=c[off:off+size]
    s=entries['style0.bin']
    image_off=u32(s,20)
    cur=24
    widgets=[]
    while cur<image_off:
        typ=u32(s,cur); seq=u32(s,cur+4); idxsz=u32(s,cur+12)
        size=idxsz&0xffff; g=idxsz>>16
        words=[u32(s,cur+36+4*j) for j in range((size-36)//4)]
        if typ==3 and seq in (2,3,10,11,69):
            widgets.append({'g':g,'seq':seq,'x':i16(s,cur+24),'y':i16(s,cur+26),'storedW':u16(s,cur+28),'storedH':u16(s,cur+30),'pointers':words})
        cur+=size
    images=[]
    cur=image_off
    idx=0
    first=image_off
    while cur<len(s):
        w=u16(s,cur); h=u16(s,cur+2); fmt=u16(s,cur+4); reserved=u16(s,cur+6); data_size=u32(s,cur+8)
        rec_size=12+data_size
        images.append({'index':idx,'relative':cur-first,'w':w,'h':h,'format':fmt,'reserved':reserved,'size':rec_size})
        cur+=rec_size; idx+=1
    byrel={im['relative']:im for im in images}
    for widget in widgets:
        widget['frames']=[byrel.get(p, {'missing':p}) for p in widget['pointers']]
        widget['frameIndices']=[byrel[p]['index'] for p in widget['pointers'] if p in byrel]
        widget['frameDims']=sorted(set((byrel[p]['w'],byrel[p]['h'],byrel[p]['format']) for p in widget['pointers'] if p in byrel))
    time=[w for w in widgets if w['seq'] in (2,3,10,11)]
    all_indices=set(i for w in time for i in w['frameIndices'])
    shared=[]
    for i in sorted(all_indices):
        consumers=[w['seq'] for w in time if i in w['frameIndices']]
        shared.append({'imageIndex':i,'consumers':consumers,'w':images[i]['w'],'h':images[i]['h'],'format':images[i]['format']})
    print('TIME_SPRITE_JSON='+json.dumps({'widgets':widgets,'timePool':shared,'timePoolCount':len(all_indices)},separators=(',',':')))

if __name__=='__main__': main()
