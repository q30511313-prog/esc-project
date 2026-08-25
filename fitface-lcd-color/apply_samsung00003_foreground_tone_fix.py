#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

old = '''        // Only the black style has the three separator bars baked into the panel
        // background. Diagnostics on the stock Samsung 00003 binary proved these
'''

new = '''        // Samsung 00003 stores the four data blocks around the clock in VALUE
        // (Pair) and COMPOSITE records. Their stock style3 foreground is the cool
        // blue/lilac #D6E1F9, which is visibly different from a recolored clock.
        // Once this exact face has passed the proven six-Sprite clock signature
        // gate in the caller, put only the documented color words on the same LCD
        // axis as the clock. All binding/value/layout words remain byte-identical.
        val targetArgb =
            (0xFFL shl 24) or
                (red.toLong() shl 16) or
                (green.toLong() shl 8) or
                blue.toLong()
        records.forEach { record ->
            val colorWordIndex = when (record.widgetType) {
                WIDGET_PAIR -> 0
                WIDGET_COMP -> 13
                else -> return@forEach
            }
            val current = record.words.getOrNull(colorWordIndex) ?: return@forEach
            // The Samsung foreground colors observed in this face are opaque ARGB.
            // Refuse unfamiliar/non-opaque encodings rather than guessing at them.
            if ((current ushr 24) != 0xFFL || current == targetArgb) return@forEach

            val absolute = entry.offset +
                record.recordOffset +
                WIDGET_FIXED_SIZE +
                colorWordIndex * 4
            repeat(4) { byteIndex ->
                val replacement =
                    ((targetArgb ushr (byteIndex * 8)) and 0xFF).toByte()
                if (output[absolute + byteIndex] != replacement) changed++
                output[absolute + byteIndex] = replacement
            }
        }

        // Only the black style has the three separator bars baked into the panel
        // background. Diagnostics on the stock Samsung 00003 binary proved these
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one Samsung chrome foreground anchor, found {count}")

path.write_text(text.replace(old, new, 1))
print("Samsung 00003 full foreground LCD tone fix applied")
