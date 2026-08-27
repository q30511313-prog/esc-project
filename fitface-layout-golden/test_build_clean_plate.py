#!/usr/bin/env python3
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from build_clean_plate import D1_DYNAMIC_REGIONS, D1_SOURCE_SHA256, build_clean_plate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("GOLDEN_D1_ARTWORK", ROOT / "fitface-layout-golden/assets/1000028944.png"))
RECIPE = ROOT / "fitface-layout/layout_recipes_v1.json"


def bright_count(image, box, threshold=70):
    return sum(1 for value in image.crop(box).convert("L").getdata() if value > threshold)


def dynamic_union_mask(size):
    mask = Image.new("1", size, 0)
    pixels = mask.load()
    for x0, y0, x1, y1 in D1_DYNAMIC_REGIONS.values():
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[x, y] = 1
    return mask


class CleanPlateContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "clean.png"

    def tearDown(self):
        self.temp.cleanup()

    def test_real_d1_identity_is_locked(self):
        self.assertEqual((978, 1536), Image.open(SOURCE).size)
        self.assertEqual(D1_SOURCE_SHA256, hashlib.sha256(SOURCE.read_bytes()).hexdigest())

    def test_is_deterministic_256x402_and_writes_only_dynamic_regions(self):
        first = build_clean_plate(SOURCE, RECIPE, self.output)
        first_bytes = self.output.read_bytes()
        second = build_clean_plate(SOURCE, RECIPE, self.output)
        self.assertEqual(first_bytes, self.output.read_bytes())
        self.assertEqual(first["sha256"], second["sha256"])

        clean = Image.open(self.output).convert("RGB")
        scaled = Image.open(SOURCE).convert("RGB").resize((256, 402), Image.Resampling.LANCZOS)
        self.assertEqual((256, 402), clean.size)
        diff = ImageChops.difference(clean, scaled)
        outside = Image.new("RGB", clean.size, "black")
        outside.paste(diff, mask=ImageChops.invert(dynamic_union_mask(clean.size).convert("L")))
        self.assertIsNone(outside.getbbox())

    def test_static_punctuation_and_frames_are_byte_identical_to_downscale(self):
        build_clean_plate(SOURCE, RECIPE, self.output)
        clean = Image.open(self.output).convert("RGB")
        scaled = Image.open(SOURCE).convert("RGB").resize((256, 402), Image.Resampling.LANCZOS)
        anchors = {
            "date_year_suffix": (109, 48, 121, 64),
            "date_month_suffix": (143, 48, 157, 64),
            "date_day_suffix": (179, 48, 191, 64),
            "time_colon": (114, 151, 130, 199),
            "battery_outline_left": (47, 337, 51, 355),
            "battery_outline_top": (47, 337, 74, 341),
            "outer_frame": (12, 6, 244, 18),
            "water_resist": (132, 366, 211, 384),
        }
        for name, box in anchors.items():
            self.assertIsNone(ImageChops.difference(clean.crop(box), scaled.crop(box)).getbbox(), name)

    def test_sample_live_values_and_battery_fill_are_removed(self):
        build_clean_plate(SOURCE, RECIPE, self.output)
        clean = Image.open(self.output).convert("RGB")
        scaled = Image.open(SOURCE).convert("RGB").resize((256, 402), Image.Resampling.LANCZOS)
        samples = {
            "weekday": (107, 80, 149, 94),
            "ampm": (48, 120, 73, 136),
            "time_left": (77, 139, 112, 212),
            "time_right": (132, 139, 205, 212),
            "seconds": (48, 257, 95, 287),
            "weather_text": (112, 301, 149, 317),
            "temperature": (171, 260, 213, 285),
            "battery_percent": (82, 336, 117, 357),
            "battery_fill": (51, 341, 70, 350),
        }
        for name, box in samples.items():
            before = bright_count(scaled, box)
            after = bright_count(clean, box)
            self.assertGreater(before, 20, name)
            self.assertLess(after, before * 0.35, f"{name}: before={before} after={after}")
        self.assertGreater(bright_count(clean, (47, 337, 75, 357)), 20)

    def test_rejects_modified_artwork(self):
        bad = Path(self.temp.name) / "bad.png"
        image = Image.open(SOURCE).convert("RGB")
        image.putpixel((0, 0), (1, 2, 3))
        image.save(bad)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            build_clean_plate(bad, RECIPE, self.output)


if __name__ == "__main__":
    unittest.main()
