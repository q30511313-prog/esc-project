#!/usr/bin/env python3
"""Render the exact Samsung 00049 seq69 weather frames into a diagnostic PNG sheet."""

from pathlib import Path
import struct
import sys
import zlib


def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]


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


def rgb565(value):
    r=(value>>11)&31; g=(value>>5)&63; b=value&31
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2))


def png_write(path,width,height,rgba):
    def chunk(kind,payload):
        import binascii
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',binascii.crc32(kind+payload)&0xffffffff)
    raw=bytearray()
    stride=width*4
    for y in range(height):
        raw.append(0)
        raw.extend(rgba[y*stride:(y+1)*stride])
    data=b'\x89PNG\r\n\x1a\n'
    data+=chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
    data+=chunk(b'IDAT',zlib.compress(bytes(raw),9))
    data+=chunk(b'IEND',b'')
    Path(path).write_bytes(data)

# Minimal 3x5 digits for frame labels.
FONT={
'0':['111','101','101','101','111'],'1':['010','110','010','010','111'],
'2':['111','001','111','100','111'],'3':['111','001','111','001','111'],
'4':['101','101','111','001','001'],'5':['111','100','111','001','111'],
'6':['111','100','111','101','111'],'7':['111','001','010','010','010'],
'8':['111','101','111','101','111'],'9':['111','101','111','001','111']}


def draw_label(canvas,w,x,y,text,scale=2):
    for ch in text:
        glyph=FONT[ch]
        for gy,row in enumerate(glyph):
            for gx,bit in enumerate(row):
                if bit=='1':
                    for yy in range(scale):
                        for xx in range(scale):
                            px=x+gx*scale+xx; py=y+gy*scale+yy
                            off=(py*w+px)*4
                            canvas[off:off+4]=bytes((255,255,255,255))
        x+=4*scale


def main():
    if len(sys.argv)!=3: raise SystemExit('usage: render_00049_weather_contact_sheet.py CONTAINER OUT.png')
    container=Path(sys.argv[1]).read_bytes(); style=directory(container)['style0.bin']
    image_map=images(style); ptrs=pointers(style)
    scale=4; cell_w=30*scale+12; cell_h=30*scale+26; cols=6; rows=4
    width=cols*cell_w; height=rows*cell_h
    canvas=bytearray(width*height*4)
    # dark neutral background
    for i in range(width*height): canvas[i*4:i*4+4]=bytes((24,24,24,255))
    for frame,pointer in enumerate(ptrs):
        cur,fw,fh,fmt,size=image_map[pointer]
        if (fw,fh,fmt)!=(30,30,0x80): raise SystemExit(f'unexpected frame schema {frame}')
        payload=style[cur+12:cur+12+fw*fh*3]
        cx=(frame%cols)*cell_w+6; cy=(frame//cols)*cell_h+20
        draw_label(canvas,width,cx,4+(frame//cols)*cell_h,f'{frame:02d}',2)
        for y in range(fh):
            for x in range(fw):
                off=(y*fw+x)*3; value=payload[off]|(payload[off+1]<<8); alpha=payload[off+2]
                r,g,b=rgb565(value)
                # composite over dark background for faithful visibility
                for yy in range(scale):
                    for xx in range(scale):
                        px=cx+x*scale+xx; py=cy+y*scale+yy
                        dest=(py*width+px)*4
                        bg=24
                        canvas[dest]=((r*alpha+bg*(255-alpha))//255)
                        canvas[dest+1]=((g*alpha+bg*(255-alpha))//255)
                        canvas[dest+2]=((b*alpha+bg*(255-alpha))//255)
                        canvas[dest+3]=255
    png_write(sys.argv[2],width,height,canvas)
    print(f'WEATHER_CONTACT_SHEET={sys.argv[2]}')
    print(f'WEATHER_CONTACT_DIMENSIONS={width}x{height}')

if __name__=='__main__': main()
