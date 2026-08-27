#!/usr/bin/env python3
"""Apply narrowly-scoped Golden layout format additions to FitFace.

The patch is fail-closed and adds only two proven primitives needed by the Golden
Samsung 00049 build:
1. style-scoped Pair sequence remap;
2. same-count Sprite resize for the shipped RGB565 or RGB565+A trailer schema.

It deliberately does not rename the app or relax the reserved/trailer checks.
"""

from pathlib import Path
import sys


def replace(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one patch anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_format_patch.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    face_editor = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
    text = face_editor.read_text()

    if "fun remapPairSequence(" in text:
        raise SystemExit("FaceEditor.remapPairSequence already exists; refusing duplicate patch")

    anchor = "object FaceEditor {\n"
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"FaceEditor object anchor count must be 1, found {count}")

    method = r'''object FaceEditor {
    /**
     * Golden-layout primitive: rebinds exactly one existing type-5 Pair widget in
     * exactly one named style to another firmware sequence id.
     *
     * This is deliberately same-size and Pair-only. The caller must supply the
     * original global index, sequence and coordinates so an unexpected stock-face
     * revision fails closed instead of editing a look-alike record.
     */
    fun remapPairSequence(
        source: Fit3Container,
        entryBasename: String,
        globalIndex: Int,
        originalSequenceId: Int,
        x: Int,
        y: Int,
        newSequenceId: Int,
    ): ContainerEdit {
        requireEditable(source)
        if (newSequenceId !in 0..255) {
            throw Fit3FormatException("Pair sequence id must be in 0..255")
        }
        if (newSequenceId == originalSequenceId) {
            throw Fit3FormatException(
                "Pair widget already uses sequence $originalSequenceId",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val matches = FaceRecordParser.scanWidgets(entry).filter {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == globalIndex &&
                it.sequenceId == originalSequenceId &&
                it.x == x &&
                it.y == y
        }
        if (matches.size != 1) {
            throw Fit3FormatException(
                "$entryBasename: expected exactly one Pair widget with identity " +
                    "global=$globalIndex sequence=$originalSequenceId x=$x y=$y, " +
                    "found ${matches.size}",
            )
        }

        val record = matches.single()
        val output = source.toByteArray()
        val before = output.copyOf()
        val sequenceOffset = entry.offset + record.recordOffset + 0x04
        output.putU32(sequenceOffset, newSequenceId.toLong())
        val changed = (sequenceOffset until sequenceOffset + 4)
            .count { before[it] != output[it] }
        if (changed == 0) {
            throw Fit3FormatException("Pair sequence remap would not change any bytes")
        }
        return finalize(source, output, listOf(entry), changed)
    }
'''

    face_editor.write_text(text.replace(anchor, method, 1))

    # The Samsung 00049 HH:MM pool is plain RGB565 (0x82), reserved=0, trailer=4.
    # Keep exactly the already-proven format/trailer discipline but permit the opaque
    # two-byte variant alongside RGB565+A.
    replace(
        root,
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

    replace(
        root,
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

    replace(
        root,
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

    replace(
        root,
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

    print("Golden Pair remap + opaque RGB565 Sprite resize patch applied")


if __name__ == "__main__":
    main()
