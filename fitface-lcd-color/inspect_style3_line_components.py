#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct
from collections import deque, Counter

src = Path(__file__).with_name('inspect_clock_background.py')
spec = importlib.util.spec_from_file_location('clockbg', src)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

data=mod.data; u16=mod.u16; u32=mod.u32
for path,off,size in mod.entries:
    if not path.endswith('/style3.bin'):
        continue
    e=data[off:off+size]; imageoff=u32(e,20)
    q=imageoff
    w,h,fmt,ds=u16(e,q),u16(e,q+2),u16(e,q+4),u32(e,q+8)
    if fmt != 0x0080:
        raise SystemExit(f'style3 background expected RGB565+A, got 0x{fmt:04X}')
    pix=e[q+12:q+12+ds]; bpp=3
    def sample(x,y):
        p=(y*w+x)*bpp
        return struct.unpack_from('<H',pix,p)[0], pix[p+2]
    # Foreground/chrome candidates are non-black RGB pixels. Transparent black rounded
    # corners are excluded, so they can never be mistaken for separator artwork.
    pts={(x,y) for y in range(h) for x in range(w) if sample(x,y)[0] != 0}
    comps=[]
    while pts:
        seed=pts.pop(); stack=[seed]; comp=[seed]
        while stack:
            x,y=stack.pop()
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in pts:
                    pts.remove(n); stack.append(n); comp.append(n)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    print('=== style3 background nonblack connected components ===')
    for i,c in enumerate(comps[:20]):
        xs=[p[0] for p in c]; ys=[p[1] for p in c]
        colors=Counter(sample(x,y) for x,y in c)
        top=[(f'0x{rgb:04X}',alpha,n) for (rgb,alpha),n in colors.most_common(8)]
        print(f'comp#{i} pixels={len(c)} bbox={min(xs)},{min(ys)}..{max(xs)},{max(ys)} top={top}')
