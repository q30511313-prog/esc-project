#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

FIT3_SIZE=(256,402)
SOURCE_SIZE=(978,1536)
DESIGN_ID="design01_8944"
SOURCE_SHA256="4167cdc079f0c27f79675f040127d731674037c5664354e06d185bab369dce2c"
THRESHOLD=24
INPAINT_RADIUS=3

@dataclass(frozen=True)
class Rect:
    name:str; x:int; y:int; w:int; h:int

DYNAMIC_SEARCH_RECTS=(
    Rect("date_year_digits",65,47,44,17),
    Rect("date_month_digit",133,47,10,17),
    Rect("date_day_digit",168,47,9,17),
    Rect("weekday",107,80,42,14),
    Rect("am_pm",48,120,25,16),
    Rect("sample_time_all",77,139,127,73),
    Rect("seconds",48,257,47,30),
    Rect("weather_icon_cloud",107,264,43,18),
    Rect("weather_icon_rain",115,282,28,10),
    Rect("weather_text",112,301,37,16),
    Rect("temperature",171,260,42,25),
    Rect("battery_fill",51,341,19,13),
    Rect("battery_percent",82,336,35,21),
)

PROTECTED_RECTS=(
    Rect("date_year_suffix",109,49,11,15),
    Rect("date_month_suffix",144,49,12,15),
    Rect("date_day_suffix",179,49,12,15),
    Rect("battery_outline_left",47,337,4,20),
    Rect("battery_outline_right",70,337,4,20),
)

COLON_SOURCE=Rect("sample_colon",118,156,8,39)
COLON_TARGET=Rect("final_colon",134,156,8,39)

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def validate_contract()->None:
    for r in DYNAMIC_SEARCH_RECTS+PROTECTED_RECTS+(COLON_SOURCE,COLON_TARGET):
        if r.w<=0 or r.h<=0 or r.x<0 or r.y<0 or r.x+r.w>256 or r.y+r.h>402:
            raise ValueError(f"invalid rect {r}")
    for p in PROTECTED_RECTS:
        for d in DYNAMIC_SEARCH_RECTS:
            if d.name=="sample_time_all":
                continue
            overlap=not(d.x+d.w<=p.x or p.x+p.w<=d.x or d.y+d.h<=p.y or p.y+p.h<=d.y)
            if overlap:
                raise ValueError(f"{d.name} overlaps protected {p.name}")

def _masked_inpaint(rgb:np.ndarray)->tuple[np.ndarray,np.ndarray]:
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    search=np.zeros(gray.shape,np.uint8)
    for r in DYNAMIC_SEARCH_RECTS:
        search[r.y:r.y+r.h,r.x:r.x+r.w]=255
    mask=np.where((search>0)&(gray>THRESHOLD),255,0).astype(np.uint8)
    mask=cv2.dilate(mask,np.ones((3,3),np.uint8),iterations=1)
    for r in PROTECTED_RECTS:
        mask[r.y:r.y+r.h,r.x:r.x+r.w]=0
    bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
    clean=cv2.inpaint(bgr,mask,INPAINT_RADIUS,cv2.INPAINT_TELEA)
    return cv2.cvtColor(clean,cv2.COLOR_BGR2RGB),mask

def _paste_static_colon(clean:np.ndarray, baseline:np.ndarray)->None:
    s=COLON_SOURCE; t=COLON_TARGET
    crop=baseline[s.y:s.y+s.h,s.x:s.x+s.w].copy()
    g=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
    alpha=(g>THRESHOLD)
    target=clean[t.y:t.y+t.h,t.x:t.x+t.w]
    target[alpha]=crop[alpha]

def build_clean_plate(source:Path,output:Path,manifest:Path|None=None)->dict:
    validate_contract()
    if sha256_file(source)!=SOURCE_SHA256:
        raise ValueError("D1 source SHA-256 mismatch")
    with Image.open(source) as im:
        if im.size!=SOURCE_SIZE:
            raise ValueError(f"D1 source size {im.size} != {SOURCE_SIZE}")
        baseline=np.array(im.convert("RGB").resize(FIT3_SIZE,Image.Resampling.LANCZOS))
    clean,mask=_masked_inpaint(baseline)
    _paste_static_colon(clean,baseline)
    for r in PROTECTED_RECTS:
        if not np.array_equal(
            baseline[r.y:r.y+r.h,r.x:r.x+r.w],
            clean[r.y:r.y+r.h,r.x:r.x+r.w],
        ):
            raise RuntimeError(f"protected region changed: {r.name}")
    output.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(clean,"RGB").save(output,format="PNG",compress_level=9)
    report={
        "schema":2,"designId":DESIGN_ID,"sourceSha256":SOURCE_SHA256,
        "sourceSize":list(SOURCE_SIZE),"outputSize":list(FIT3_SIZE),
        "resampler":"Pillow LANCZOS",
        "reconstruction":"OpenCV TELEA deterministic inpaint",
        "threshold":THRESHOLD,"inpaintRadius":INPAINT_RADIUS,
        "maskedPixels":int(np.count_nonzero(mask)),
        "changedPixels":int(np.count_nonzero(np.any(baseline!=clean,axis=2))),
        "colonSource":asdict(COLON_SOURCE),"colonTarget":asdict(COLON_TARGET),
        "dynamicSearchRects":[asdict(r) for r in DYNAMIC_SEARCH_RECTS],
        "protectedRects":[asdict(r) for r in PROTECTED_RECTS],
    }
    if report["changedPixels"]<=0:
        raise RuntimeError("clean plate unchanged")
    report["outputSha256"]=sha256_file(output)
    if manifest:
        manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    ap.add_argument("output",type=Path)
    ap.add_argument("--manifest",type=Path)
    a=ap.parse_args()
    print(json.dumps(build_clean_plate(a.source,a.output,a.manifest),ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
