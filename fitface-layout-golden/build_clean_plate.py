#!/usr/bin/env python3
"""Deterministic Design-1 clean-plate builder for the Fit3 Golden layout.

No generative image editing is used. The approved source artwork is identity-locked,
resized with Pillow LANCZOS, and only bounded sample/live-value strokes are locally
reconstructed. Pixels outside those regions are never written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image

D1_SOURCE_SHA256 = "4167cdc079f0c27f79675f040127d731674037c5664354e06d185bab369dce2c"
D1_SOURCE_SIZE = (978, 1536)
FIT3_SIZE = (256, 402)

# Half-open Fit3 boxes. DATE excludes 년/월/일, TIME excludes ':', and the battery
# mask removes sample fill bars while leaving its decorative shell in the clean plate.
D1_DYNAMIC_REGIONS: Dict[str, Tuple[int, int, int, int]] = {
    "DATE_YEAR_VALUE": (65, 47, 108, 64),
    "DATE_MONTH_VALUE": (132, 47, 143, 64),
    "DATE_DAY_VALUE": (167, 47, 179, 64),
    "WEEKDAY_VALUE": (107, 80, 149, 94),
    "AM_PM_VALUE": (48, 120, 73, 136),
    "TIME_LEFT_VALUE": (77, 139, 112, 212),
    "TIME_RIGHT_VALUES": (132, 139, 205, 212),
    "SECONDS_VALUE": (48, 257, 95, 287),
    "WEATHER_ICON_VALUE": (108, 253, 149, 290),
    "WEATHER_TEXT_VALUE": (112, 301, 149, 317),
    "TEMP_VALUE": (171, 260, 213, 285),
    "BATTERY_PERCENT_VALUE": (82, 336, 117, 357),
    "BATTERY_SAMPLE_FILL": (51, 341, 70, 350),
}

EXPECTED_D1_BOXES = {
    "DATE": [65, 47, 126, 17],
    "WEEKDAY": [107, 80, 42, 14],
    "AM_PM": [48, 120, 25, 16],
    "TIME": [77, 139, 127, 73],
    "SECONDS": [48, 257, 47, 30],
    "WEATHER_ICON": [98, 253, 59, 46],
    "WEATHER_TEXT": [112, 301, 37, 16],
    "TEMP": [171, 260, 42, 25],
    "BATTERY_ICON": [47, 337, 27, 20],
    "BATTERY_PERCENT": [82, 336, 35, 21],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_d1_recipe(recipe_path: Path) -> dict:
    data = json.loads(recipe_path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("layout recipe schema must be 1")
    if data.get("sourceCanvas") != {"width": 978, "height": 1536}:
        raise ValueError("layout recipe sourceCanvas must be 978x1536")
    if data.get("fit3Canvas") != {"width": 256, "height": 402}:
        raise ValueError("layout recipe fit3Canvas must be 256x402")

    matches = [design for design in data.get("designs", []) if design.get("id") == "design01_8944"]
    if len(matches) != 1:
        raise ValueError("layout recipe must contain exactly one design01_8944")
    d1 = matches[0]
    if d1.get("sourceFile") != "1000028944.png":
        raise ValueError("design01_8944 sourceFile must be 1000028944.png")

    boxes = d1.get("boxes", {})
    for name, expected in EXPECTED_D1_BOXES.items():
        box = boxes.get(name, {}).get("fit3Px", {})
        actual = [box.get("x"), box.get("y"), box.get("w"), box.get("h")]
        if actual != expected:
            raise ValueError(f"D1 {name} fit3 box drifted: {actual} != {expected}")
    return d1


def _dilate(mask: np.ndarray, radius: int = 1) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    padded = np.pad(mask, radius, mode="constant", constant_values=False)
    output = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            output |= padded[dy:dy + height, dx:dx + width]
    return output


def _reconstruct_region(
    pixels: np.ndarray,
    box: Tuple[int, int, int, int],
    threshold: int = 28,
) -> int:
    x0, y0, x1, y1 = box
    region = pixels[y0:y1, x0:x1]
    if region.size == 0:
        raise ValueError(f"empty dynamic region {box}")

    rgb = region.astype(np.int32)
    luminance = (77 * rgb[:, :, 0] + 150 * rgb[:, :, 1] + 29 * rgb[:, :, 2] + 128) // 256
    mask = _dilate(luminance >= threshold, 1)
    if not mask.any():
        return 0

    original = region.copy()
    height, width = mask.shape
    background_pixels = original[~mask]
    fallback = (
        np.percentile(background_pixels, 30, axis=0).astype(np.uint8)
        if len(background_pixels)
        else np.zeros(3, dtype=np.uint8)
    )

    for y in range(height):
        x = 0
        while x < width:
            if not mask[y, x]:
                x += 1
                continue
            start = x
            while x < width and mask[y, x]:
                x += 1
            end = x

            left = start - 1
            while left >= 0 and mask[y, left]:
                left -= 1
            right = end
            while right < width and mask[y, right]:
                right += 1

            if left >= 0 and right < width:
                left_color = original[y, left].astype(np.float64)
                right_color = original[y, right].astype(np.float64)
                span = right - left
                for target_x in range(start, end):
                    factor = (target_x - left) / span
                    region[y, target_x] = np.rint(
                        left_color * (1.0 - factor) + right_color * factor,
                    ).astype(np.uint8)
            elif left >= 0:
                region[y, start:end] = original[y, left]
            elif right < width:
                region[y, start:end] = original[y, right]
            else:
                region[y, start:end] = fallback

    return int(np.count_nonzero(np.any(region != original, axis=2)))


def build_clean_plate(
    source_path: Path | str,
    recipe_path: Path | str,
    output_path: Path | str,
) -> dict:
    source_path = Path(source_path)
    recipe_path = Path(recipe_path)
    output_path = Path(output_path)

    if _sha256(source_path) != D1_SOURCE_SHA256:
        raise ValueError("D1 artwork SHA-256 does not match the approved source")

    with Image.open(source_path) as opened:
        source = opened.convert("RGB")
    if source.size != D1_SOURCE_SIZE:
        raise ValueError(f"D1 artwork must be {D1_SOURCE_SIZE[0]}x{D1_SOURCE_SIZE[1]}")
    _load_d1_recipe(recipe_path)

    scaled = source.resize(FIT3_SIZE, Image.Resampling.LANCZOS)
    pixels = np.array(scaled, dtype=np.uint8, copy=True)
    per_region = {
        name: _reconstruct_region(pixels, box)
        for name, box in D1_DYNAMIC_REGIONS.items()
    }
    changed_pixels = sum(per_region.values())
    if changed_pixels <= 0:
        raise ValueError("clean-plate masking changed no pixels")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels, mode="RGB").save(
        output_path,
        format="PNG",
        optimize=False,
        compress_level=9,
    )
    return {
        "source_sha256": D1_SOURCE_SHA256,
        "sha256": _sha256(output_path),
        "width": FIT3_SIZE[0],
        "height": FIT3_SIZE[1],
        "changed_pixels": changed_pixels,
        "regions": per_region,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--recipe", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = build_clean_plate(args.source, args.recipe, args.output)
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
