#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

# v11 is intentionally a narrow layer on top of the proven v10 Samsung 00003
# optical-calibration patch. The user-facing target stays #B8B8AD; only the
# Samsung 00003/style3 hardware payload changes to the real-device-selected
# calibration patch 15 representative RGB888 #B5B6BD, which rounds to
# RGB565 0xB5B7 (R5=22, G6=45, B5=23).
replacements = {
    "val opticalClockRed = if (useFit3OpticalCalibration) 0xB8 else red":
        "val opticalClockRed = if (useFit3OpticalCalibration) 0xB5 else red",
    "val opticalClockGreen = if (useFit3OpticalCalibration) 0xC0 else green":
        "val opticalClockGreen = if (useFit3OpticalCalibration) 0xB6 else green",
    "val opticalClockBlue = if (useFit3OpticalCalibration) 0xA1 else blue":
        "val opticalClockBlue = if (useFit3OpticalCalibration) 0xBD else blue",
}

for old, new in replacements.items():
    count = text.count(old)
    if count != 2:
        raise SystemExit(f"FaceEditor.kt: expected two v10 optical anchors for {old!r}, found {count}")
    text = text.replace(old, new)

path.write_text(text)
print("Samsung 00003 style3 v11 patch15 optical calibration #B5B6BD / RGB565 0xB5B7 applied")
