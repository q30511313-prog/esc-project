#!/usr/bin/env python3
"""Report dominant visible RGB565 colors for Samsung 00049 seq69 weather frames."""

from collections import Counter
from pathlib import Path
import struct
import sys


def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]


def rgb565_to_rgb(value):
    r=(value>>11)&0x1f; g=(value>>5)&0x3f; b=value&0x1f
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2))


def directory(data):
    out={}
    for i in range(u32(data,12)):
        ro=32+i*74; raw=data[ro:ro+74]
        name=Path(raw[:64].split(b'\0',1)[0].decode('utf-8','replace')).name
        off=u32(raw,64); size=u32(raw,68)
        out[name]=data[off:off+size]
    return out


def images(style):
    start=u32(style,20); cur=start; out={}
    while cur<len(style):
        w=u16(style,cur); h=u16(style,cur+2); fmt=u16(style,cur+4); size=u32(style,cur+8)
        out[cur-start]=(cur,w,h,fmt,size)
        cur+=12+size
    return out


def pointers(style):
    end=u32(style,20); cur=24
    while cur<end:
        typ=u32(style,cur); seq=u32(style,cur+4); rs=u32(style,cur+12)&0xffff
        if typ==3 and seq==69:
            n=u32(style,cur+32)
            return [u32(style,cur+36+i*4) for i in range(n)]
        cur+=rs
    raise SystemExit('seq69 not found')


def main():
    if len(sys.argv)!=2: raise SystemExit('usage: inspect_00049_weather_colors.py CONTAINER')
    container=Path(sys.argv[1]).read_bytes(); style=directory(container)['style0.bin']
    image_map=images(style)
    for frame,pointer in enumerate(pointers(style)):
        cur,w,h,fmt,size=image_map[pointer]
        if fmt!=0x80: raise SystemExit(f'frame {frame}: unexpected fmt {fmt}')
        payload=style[cur+12:cur+12+w*h*3]
        colors=Counter()
        alpha_total=0
        visible=0
        for i in range(w*h):
            lo=payload[i*3]; hi=payload[i*3+1]; alpha=payload[i*3+2]
            if alpha<32: continue
            value=lo|(hi<<8)
            weight=alpha
            colors[value]+=weight
            alpha_total+=alpha
            visible+=1
        tops=[]
        for value,weight in colors.most_common(6):
            rgb=rgb565_to_rgb(value)
            tops.append(f'0x{value:04X}=#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}:{weight}')
        print(f'WEATHER_COLOR_{frame:02d}=visible:{visible},alpha:{alpha_total},top:'+';'.join(tops))

if __name__=='__main__': main()
