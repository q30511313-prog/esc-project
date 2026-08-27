#!/usr/bin/env python3
import json
from pathlib import Path
import struct
import sys


def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def directory(data):
    out=[]
    for i in range(u32(data,12)):
        ro=32+i*74
        raw=data[ro:ro+74]
        path=raw[:64].split(b'\0',1)[0].decode('utf-8','replace')
        off=u32(raw,64); size=u32(raw,68)
        out.append((path,data[off:off+size]))
    return out


def inspect(path):
    data=Path(path).read_bytes()
    entries=directory(data)
    locale=[]
    fonts=[]
    for p,b in entries:
        bn=Path(p).name
        if bn=='font_ko.bin':
            count=u32(b,8)
            groups=[]
            for g in range(count):
                ln=u32(b,0x18+g*8)
                rel=u32(b,0x1c+g*8)
                raw=b[rel:rel+ln]
                groups.append({'index':g,'length':ln,'offset':rel,'text':raw.decode('utf-8','replace'),'hex':raw.hex()})
            locale={'path':p,'bytes':len(b),'count':count,'headerHex':b[:0x18].hex(),'groups':groups}
        if bn.startswith('font_') and len(b)==92:
            role=b[0x48:0x58].split(b'\0',1)[0].decode('ascii','replace')
            fonts.append({'path':p,'basename':bn,'bytes':len(b),'role':role,'hex':b.hex()})
    return {'container':str(path),'fontKo':locale,'fontBindings':fonts}


def main():
    if len(sys.argv)<2: raise SystemExit('usage: inspect_stock_locale.py CONTAINER [CONTAINER...]')
    for path in sys.argv[1:]:
        print('LOCALE_INSPECT_JSON='+json.dumps(inspect(path),ensure_ascii=False,separators=(',',':')))

if __name__=='__main__': main()
