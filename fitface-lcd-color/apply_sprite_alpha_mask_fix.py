#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()
old = '''                    val existing = output.u16(absolute)
                    val replacement = SpriteTint.tintRgb565(existing, red, green, blue)
                    if (replacement == existing) return@repeat
'''
new = '''                    val existing = output.u16(absolute)
                    val replacement = if (image.format == IMAGE_RGB565_ALPHA) {
                        val alpha = output[absolute + 2].toInt() and 0xFF
                        SpriteTint.tintRgb565AlphaMask(
                            pixel = existing,
                            alpha = alpha,
                            targetRed = red,
                            targetGreen = green,
                            targetBlue = blue,
                        )
                    } else {
                        SpriteTint.tintRgb565(existing, red, green, blue)
                    }
                    if (replacement == existing) return@repeat
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one sprite tint anchor, found {count}")
path.write_text(text.replace(old, new, 1))
print("RGB565+A sprite alpha-mask recolor fix applied")
