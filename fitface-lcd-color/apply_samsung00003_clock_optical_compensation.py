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


# Real-watch photos show Samsung 00003 style3's RGB565 clock path rendering about
# five percent bluer than its VALUE/COMPOSITE ARGB text even when both receive the
# same requested #B8B8AD. Keep the user's canonical ARGB request intact and warm
# only the proven style3 clock raster path to B8/B8/A5.
#
# The full-foreground signature is deliberate: it narrows this calibration to the
# actual dashboard schema and leaves minimal clock-only fixtures / unrelated faces
# on the ordinary color transform.
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
            val opticalClockBlue = if (
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
            val background = FaceRecordParser.backgroundImage(entry)?.index
''',
)
replace_in_function(
    "recolorSpriteWidgetAcrossStyles",
    '''                            targetBlue = blue,
''',
    '''                            targetBlue = opticalClockBlue,
''',
)
replace_in_function(
    "recolorSpriteWidgetAcrossStyles",
    '''                        SpriteTint.tintRgb565(existing, red, green, blue)
''',
    '''                        SpriteTint.tintRgb565(existing, red, green, opticalClockBlue)
''',
)

# The two colon rasters and the three separator bars share the RGB565 display path.
# Apply the same renderer-specific blue compensation there, while the targetArgb
# block below intentionally continues to use the original requested blue (0xAD).
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
        val opticalClockBlue = if (
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
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''                    targetBlue = blue,
''',
    '''                    targetBlue = opticalClockBlue,
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''                SpriteTint.tintRgb565(existing, red, green, blue)
''',
    '''                SpriteTint.tintRgb565(existing, red, green, opticalClockBlue)
''',
)
replace_in_private_function(
    "tintSamsung00003CasioClockChrome",
    '''            val replacement = SpriteTint.tintRgb565(existing, red, green, blue)
''',
    '''            val replacement = SpriteTint.tintRgb565(existing, red, green, opticalClockBlue)
''',
)

path.write_text(text)
print("Samsung 00003 style3 optical clock compensation applied")
