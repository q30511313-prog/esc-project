#!/usr/bin/env python3
import json
import pathlib
import struct
import sys


def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]


def main():
    container=pathlib.Path(sys.argv[1]).read_bytes()
    entries={}
    for i in range(u32(container,12)):
        r=32+i*74
        name=pathlib.Path(container[r:r+64].split(b'\0',1)[0].decode()).name
        off=u32(container,r+64); size=u32(container,r+68)
        entries[name]=container[off:off+size]
    style=entries['style0.bin']
    image_off=u32(style,20)
    cur=24
    records=[]
    while cur<image_off:
        typ=u32(style,cur); seq=u32(style,cur+4); idxsz=u32(style,cur+12)
        size=idxsz&0xffff; g=idxsz>>16
        words=[u32(style,cur+36+4*j) for j in range((size-36)//4)]
        if g in (8,10,11):
            records.append({
                'g':g,'type':typ,'seq':seq,
                'x':i16(style,cur+24),'y':i16(style,cur+26),
                'w':u16(style,cur+28),'h':u16(style,cur+30),
                'recordSize':size,'words':[f'0x{x:08X}' for x in words]
            })
        cur+=size
    print('TEMP_BATTERY_JSON='+json.dumps(records,separators=(',',':')))

if __name__=='__main__': main()
