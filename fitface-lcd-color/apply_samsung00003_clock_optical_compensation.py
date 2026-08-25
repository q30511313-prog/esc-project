#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()


def replace_in_function(function_name: str, old: str, new: str, expected: int = 1) -> None:
    global text
    marker = f"    fun {function_name}("
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"FaceEditor.kt: function {function_name} not found")
    next_fun = text.find("\n    fun ", start + len(marker))
    next_private = text.find("\n    private fun ", start + len(marker))
    ends = [p for p in (next_fun, next_private) if p >= 0]
    end = min(ends) if ends else len(text)
    block = text[start:end]
    count = block.count(old)
    if count != expected:
        raise SystemExit(
            f"FaceEditor.kt:{function_name}: expected {expected} patch anchor(s), found {count}"
        )
    block = block.replace(old, new)
    text = text[:start] + block + text[end:]


def replace_in_private_function(function_name: str, old: str, new: str, expected: int = 1) -> None:
    global text
    marker = f"    private fun {function_name}("
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"FaceEditor.kt: private function {function_name} not found")
    next_fun = text.find("\n    fun ", start + len(marker))
    next_private = text.find("\n    private fun ", start + len(marker))
    ends = [p for p in (next_fun, next_private) if p >= 0]
    end = min(ends) if ends else len(text)
    block = text[start:end]
    count = block.count(old)
    if count != expected:
        raise SystemExit(
            f"FaceEditor.kt:{function_name}: expected {expected} patch anchor(s), found {count}"
        )
    block = block.replace(old, new)
    text = text[:start] + block + text[end:]


# The logical/user-facing Casio tone remains #B8B8AD. Real Fit3 captures show
# that this neutral input is emitted as lavender: Green is suppressed while Blue
# is elevated. For only the proven Samsung 00003 black style, apply the inverse
# optical payload #B8C794. Other faces, styles, and requested colors stay on the
# ordinary transform. RGB565 quantizes the calibrated payload to 0xB631.
replace_in_function(
    "recolorSpriteWidgetAcrossStyles",
    '''            val background = FaceRecordParser.backgroundImage(entry)?.index
''',
    '''            val hasSamsung00003ForegroundSignature =
                records.any {
                    it.widgetType == WIDGET_PAIR &&
                        it.words.getOrNull(0)?.ushr(24) == 0xFFL
                } &&
                records.any {
                    it.widgetType == WIDGET_COMP &&
                        it.words.getOrNull(13)?.ushr(24) == 0xFFL
                }
            val useFit3OpticalCalibration =
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
            val background = FaceRecordParser.backgroundImage(entry)?.index
''',
)
replace_in_function(
    "recolorSpriteWidgetAcrossStyles",
    '''                            targetRed = red,
                            targetGreen = green,
                            targetBlue = blue,
''',
    '''                            targetRed = opticalClockRed,
                            targetGreen = opticalClockGreen,
                            targetBlue = opticalClockBlue,
''',
)
replace_in_function(
    "recolorSpriteWidgetAcrossStyles",
    '''                        SpriteTint.tintRgb565(existing, red, green, blue)
''',
    '''                        SpriteTint.tintRgb565(
                            existing,
                            opticalClockRed,
                            opticalClockGreen,
                            opticalClockBlue,
                        )
''',
)

# The two colon rasters and the three separator bars use RGB565 as well. VALUE /
# COMPOSITE foreground words are ARGB, but the same inverse optical payload must
# be encoded there too so every renderer path converges perceptually on one tone.
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''        val imagesByRelativeOffset = images.associateBy {
            (it.recordOffset - firstImageOffset).toLong()
        }
''',
    '''        val imagesByRelativeOffset = images.associateBy {
            (it.recordOffset - firstImageOffset).toLong()
        }
        val hasSamsung00003ForegroundSignature =
            records.any {
                it.widgetType == WIDGET_PAIR &&
                    it.words.getOrNull(0)?.ushr(24) == 0xFFL
            } &&
            records.any {
                it.widgetType == WIDGET_COMP &&
                    it.words.getOrNull(13)?.ushr(24) == 0xFFL
            }
        val useFit3OpticalCalibration =
            entry.basename == "style3.bin" &&
                entry.path.contains("/SM-R390_00003_256x402/") &&
                hasSamsung00003ForegroundSignature &&
                red == 0xB8 &&
                green == 0xB8 &&
                blue == 0xAD
        val opticalClockRed = if (useFit3OpticalCalibration) 0xB8 else red
        val opticalClockGreen = if (useFit3OpticalCalibration) 0xC7 else green
        val opticalClockBlue = if (useFit3OpticalCalibration) 0x94 else blue
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''                    targetRed = red,
                    targetGreen = green,
                    targetBlue = blue,
''',
    '''                    targetRed = opticalClockRed,
                    targetGreen = opticalClockGreen,
                    targetBlue = opticalClockBlue,
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''                SpriteTint.tintRgb565(existing, red, green, blue)
''',
    '''                SpriteTint.tintRgb565(
                    existing,
                    opticalClockRed,
                    opticalClockGreen,
                    opticalClockBlue,
                )
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''            val replacement = SpriteTint.tintRgb565(existing, red, green, blue)
''',
    '''            val replacement = SpriteTint.tintRgb565(
                existing,
                opticalClockRed,
                opticalClockGreen,
                opticalClockBlue,
            )
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''        val targetArgb =
            (0xFFL shl 24) or
                (red.toLong() shl 16) or
                (green.toLong() shl 8) or
                blue.toLong()
''',
    '''        val targetArgb =
            (0xFFL shl 24) or
                (opticalClockRed.toLong() shl 16) or
                (opticalClockGreen.toLong() shl 8) or
                opticalClockBlue.toLong()
''',
)

path.write_text(text)
print("Samsung 00003 style3 full optical warm-gray calibration #B8C794 applied")
