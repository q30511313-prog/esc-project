#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def replace(path: str, old: str, new: str) -> None:
    p = root / path
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one patch anchor, found {count}")
    p.write_text(text.replace(old, new, 1))

# 1) Offer Sprite resize for the same proven geometry/pointer schema when the
# raster pool is plain RGB565 as well as RGB565+A. Opaque frames paint their full
# rectangle, which the UI already warns about separately.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt",
    '''                poolSignatures.size == 1 &&
                poolImages.first().let { image ->
                    image.format == IMAGE_RGB565_ALPHA &&
                        image.reserved == 0 &&
                        image.opaqueTrailerSize == 4
                }
''',
    '''                poolSignatures.size == 1 &&
                poolImages.first().let { image ->
                    image.format in setOf(IMAGE_RGB565_ALPHA, IMAGE_RGB565) &&
                        image.reserved == 0 &&
                        image.opaqueTrailerSize == 4
                }
''',
)

# 2) Structural resize accepts either two-byte RGB565 or three-byte RGB565+A,
# while preserving the exact shipped format and trailer.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/StructuralEditor.kt",
    '''        if (signature[2] != IMAGE_RGB565_ALPHA || signature[3] != 0 || signature[4] != 4) {
            throw Fit3FormatException(
                "${entry.basename}: Sprite requires RGB565+A with the proven trailer schema",
            )
        }
''',
    '''        if (signature[2] !in setOf(IMAGE_RGB565_ALPHA, IMAGE_RGB565) ||
            signature[3] != 0 || signature[4] != 4
        ) {
            throw Fit3FormatException(
                "${entry.basename}: Sprite requires RGB565 or RGB565+A with the proven trailer schema",
            )
        }
''',
)

# 3) Choose a format-correct nearest-neighbour resampler. The watch's opaque
# RGB565 digit frames are exactly two bytes/pixel; do not fabricate alpha bytes.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/StructuralEditor.kt",
    '''        val resized = nearestRgb565Alpha(
            data.copyOfRange(from.pixelOffset, from.pixelOffset + from.pixelDataSize),
            from.width,
            from.height,
            width,
            height,
        )
''',
    '''        val sourcePixels = data.copyOfRange(
            from.pixelOffset,
            from.pixelOffset + from.pixelDataSize,
        )
        val resized = when (from.format) {
            IMAGE_RGB565_ALPHA -> nearestRgb565Alpha(
                sourcePixels,
                from.width,
                from.height,
                width,
                height,
            )
            IMAGE_RGB565 -> nearestRgb565Opaque(
                sourcePixels,
                from.width,
                from.height,
                width,
                height,
            )
            else -> throw Fit3FormatException(
                "Sprite resize does not support image format 0x${from.format.toString(16)}",
            )
        }
''',
)

# 4) Two-byte RGB565 nearest-neighbour helper, kept internal so the regression test
# can validate exact payload sizing without exposing it in the app API.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/StructuralEditor.kt",
    '''    private fun nearestRgb565Alpha(
''',
    '''    internal fun nearestRgb565Opaque(
        source: ByteArray,
        oldWidth: Int,
        oldHeight: Int,
        newWidth: Int,
        newHeight: Int,
    ): ByteArray {
        if (source.size != oldWidth * oldHeight * 2) {
            throw Fit3FormatException("RGB565 frame payload does not match dimensions")
        }
        val output = ByteArray(newWidth * newHeight * 2)
        repeat(newHeight) { y ->
            val sourceY = minOf(oldHeight - 1, y * oldHeight / newHeight)
            repeat(newWidth) { x ->
                val sourceX = minOf(oldWidth - 1, x * oldWidth / newWidth)
                val oldOffset = (sourceY * oldWidth + sourceX) * 2
                val newOffset = (y * newWidth + x) * 2
                source.copyInto(output, newOffset, oldOffset, oldOffset + 2)
            }
        }
        return output
    }

    private fun nearestRgb565Alpha(
''',
)

# 5) Distinguish this experimental app from both the stock app and the sequence lab.
replace(
    "app/src/main/res/values/strings.xml",
    '<string name="app_name">FitFace Studio</string>',
    '<string name="app_name">FitFace Studio Sprite Test</string>',
)

print("opaque RGB565 sprite resize patch applied")
