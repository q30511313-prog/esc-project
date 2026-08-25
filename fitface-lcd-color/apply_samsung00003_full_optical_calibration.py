#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

# This patch intentionally runs AFTER the v8 renderer-specific blue compensation.
# Real Fit3 captures proved that blue-only correction is insufficient: the panel /
# renderer combination also suppresses Green. Keep the user-facing logical request
# at #B8B8AD, but for the proven Samsung 00003 style3 foreground encode an inverse
# optical payload of #B8C794. RGB565 quantizes that to 0xB631.

main_old = '''            val opticalClockBlue = if (
                entry.basename == "style3.bin" &&
                entry.path.contains("/SM-R390_00003_256x402/") &&
                clockSprites != null &&
                hasSamsung00003ForegroundSignature &&
                red == 0xB8 &&
                green == 0xB8 &&
                blue == 0xAD
            ) {
                0xA5
            } else {
                blue
            }
'''
main_new = '''            val useFit3OpticalCalibration =
                entry.basename == "style3.bin" &&
                    entry.path.contains("/SM-R390_00003_256x402/") &&
                    clockSprites != null &&
                    hasSamsung00003ForegroundSignature &&
                    red == 0xB8 &&
                    green == 0xB8 &&
                    blue == 0xAD
            val opticalClockRed = if (useFit3OpticalCalibration) 0xB8 else red
            val opticalClockGreen = if (useFit3OpticalCalibration) 0xC7 else green
            val opticalClockBlue = if (useFit3OpticalCalibration) 0x94 else blue
'''
count = text.count(main_old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one main v8 optical block, found {count}")
text = text.replace(main_old, main_new, 1)

private_old = '''        val opticalClockBlue = if (
            entry.basename == "style3.bin" &&
            entry.path.contains("/SM-R390_00003_256x402/") &&
            hasSamsung00003ForegroundSignature &&
            red == 0xB8 &&
            green == 0xB8 &&
            blue == 0xAD
        ) {
            0xA5
        } else {
            blue
        }
'''
private_new = '''        val useFit3OpticalCalibration =
            entry.basename == "style3.bin" &&
                entry.path.contains("/SM-R390_00003_256x402/") &&
                hasSamsung00003ForegroundSignature &&
                red == 0xB8 &&
                green == 0xB8 &&
                blue == 0xAD
        val opticalClockRed = if (useFit3OpticalCalibration) 0xB8 else red
        val opticalClockGreen = if (useFit3OpticalCalibration) 0xC7 else green
        val opticalClockBlue = if (useFit3OpticalCalibration) 0x94 else blue
'''
count = text.count(private_old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one private v8 optical block, found {count}")
text = text.replace(private_old, private_new, 1)

alpha_old = '''                            targetRed = red,
                            targetGreen = green,
                            targetBlue = opticalClockBlue,
'''
alpha_new = '''                            targetRed = opticalClockRed,
                            targetGreen = opticalClockGreen,
                            targetBlue = opticalClockBlue,
'''
count = text.count(alpha_old)
if count != 2:
    raise SystemExit(f"FaceEditor.kt: expected two RGB565+A optical anchors, found {count}")
text = text.replace(alpha_old, alpha_new)

rgb_old = 'SpriteTint.tintRgb565(existing, red, green, opticalClockBlue)'
rgb_new = 'SpriteTint.tintRgb565(existing, opticalClockRed, opticalClockGreen, opticalClockBlue)'
count = text.count(rgb_old)
if count != 3:
    raise SystemExit(f"FaceEditor.kt: expected three RGB565 optical anchors, found {count}")
text = text.replace(rgb_old, rgb_new)

argb_old = '''        val targetArgb =
            (0xFFL shl 24) or
                (red.toLong() shl 16) or
                (green.toLong() shl 8) or
                blue.toLong()
'''
argb_new = '''        val targetArgb =
            (0xFFL shl 24) or
                (opticalClockRed.toLong() shl 16) or
                (opticalClockGreen.toLong() shl 8) or
                opticalClockBlue.toLong()
'''
count = text.count(argb_old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one Samsung foreground ARGB anchor, found {count}")
text = text.replace(argb_old, argb_new, 1)

path.write_text(text)
print("Samsung 00003 style3 full optical warm-gray calibration #B8C794 applied")
