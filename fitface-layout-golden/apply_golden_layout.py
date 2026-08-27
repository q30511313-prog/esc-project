#!/usr/bin/env python3
"""Install the style0-only Golden D1 clean-plate/layout compiler into FitFace.

The patch is fail-closed against the pinned upstream FaceEditor shape. It adds a
single-style background rewrite rather than calling the existing all-style helper,
then writes GoldenD1LayoutCompiler.kt which composes that rewrite with the already
proven GoldenD1Compiler semantic transaction.
"""
from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_layout.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    editor = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"

    replace_once(
        editor,
        "    fun replaceBackgrounds(\n",
        '''    fun replaceBackgroundInStyle(
        source: Fit3Container,
        entryBasename: String,
        width: Int,
        height: Int,
        argb: IntArray,
    ): ContainerEdit {
        requireEditable(source)
        if (width <= 0 || height <= 0 || argb.size != width * height) {
            throw Fit3FormatException("replacement pixel dimensions are inconsistent")
        }
        val entry = source.entryByBasename(entryBasename)
        val image = FaceRecordParser.backgroundImage(entry)
            ?: throw Fit3FormatException("$entryBasename: no panel background raster")
        if (image.width != width || image.height != height) {
            throw Fit3FormatException(
                "$entryBasename: background is ${image.width}x${image.height}, " +
                    "replacement is ${width}x$height",
            )
        }

        val output = source.toByteArray()
        var changedBytes = 0
        if (image.isIndexed) {
            val indexedPayload = IndexedImage.quantize(argb)
            val start = entry.offset + image.pixelOffset
            indexedPayload.forEachIndexed { offset, byte ->
                if (output[start + offset] != byte) changedBytes++
                output[start + offset] = byte
            }
        } else {
            repeat(argb.size) { index ->
                val color = argb[index]
                val rgb565 = encodeRgb565(
                    color ushr 16 and 0xFF,
                    color ushr 8 and 0xFF,
                    color and 0xFF,
                )
                val absolute = entry.offset + image.samplesOffset + index * image.bytesPerPixel
                val low = rgb565.toByte()
                val high = (rgb565 ushr 8).toByte()
                if (output[absolute] != low) changedBytes++
                if (output[absolute + 1] != high) changedBytes++
                output[absolute] = low
                output[absolute + 1] = high
            }
        }
        if (changedBytes == 0) {
            throw Fit3FormatException("background replacement would not change any pixels")
        }
        return finalize(source, output, listOf(entry), changedBytes)
    }

    fun replaceBackgrounds(
''',
        "style-scoped background rewrite",
    )

    compiler = root / (
        "core/format/src/main/kotlin/dev/fitface/studio/core/format/"
        "GoldenD1LayoutCompiler.kt"
    )
    compiler.write_text(
        '''package dev.fitface.studio.core.format

/**
 * Task-7 Golden assembler. Replaces only style0's full-panel background with the
 * caller-provided 256x402 clean plate, then applies the already-proven D1 live
 * semantic compiler. Sibling style payloads are asserted byte-identical.
 */
object GoldenD1LayoutCompiler {
    const val WIDTH = 256
    const val HEIGHT = 402

    fun compile(
        source: Fit3Container,
        cleanPlateArgb: IntArray,
    ): ContainerEdit {
        if (cleanPlateArgb.size != WIDTH * HEIGHT) {
            throw Fit3FormatException("Golden D1 clean plate must be 256x402")
        }

        val siblingNames = listOf("style1.bin", "style2.bin", "style3.bin")
        val siblingBytes = siblingNames.associateWith {
            source.entryByBasename(it).data.copyOf()
        }
        val beforeStyle0 = source.entryByBasename("style0.bin")
        val beforeImages = FaceRecordParser.scanImages(beforeStyle0).size
        val beforeBackground = FaceRecordParser.backgroundImage(beforeStyle0)
            ?: throw Fit3FormatException("style0.bin: Golden D1 requires a panel background")
        if (beforeBackground.width != WIDTH || beforeBackground.height != HEIGHT) {
            throw Fit3FormatException(
                "style0.bin: Golden D1 background must be ${WIDTH}x$HEIGHT",
            )
        }

        val backgroundEdit = FaceEditor.replaceBackgroundInStyle(
            source = source,
            entryBasename = "style0.bin",
            width = WIDTH,
            height = HEIGHT,
            argb = cleanPlateArgb,
        )
        val semanticEdit = GoldenD1Compiler.compile(backgroundEdit.container)
        val output = semanticEdit.container

        siblingBytes.forEach { (name, bytes) ->
            if (!bytes.contentEquals(output.entryByBasename(name).data)) {
                throw Fit3FormatException("Golden D1 layout modified sibling $name")
            }
        }

        val afterStyle0 = output.entryByBasename("style0.bin")
        val afterImages = FaceRecordParser.scanImages(afterStyle0).size
        if (afterImages != beforeImages) {
            throw Fit3FormatException(
                "Golden D1 layout changed style0 image record count: $beforeImages -> $afterImages",
            )
        }
        val afterBackground = FaceRecordParser.backgroundImage(afterStyle0)
            ?: throw Fit3FormatException("style0.bin: Golden D1 lost its panel background")
        if (afterBackground.width != WIDTH || afterBackground.height != HEIGHT) {
            throw Fit3FormatException("style0.bin: Golden D1 background geometry drifted")
        }

        val report = output.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden D1 layout failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        val changed = backgroundEdit.changedPayloadBytes + semanticEdit.changedPayloadBytes
        if (changed <= 0) {
            throw Fit3FormatException("Golden D1 layout would not change any bytes")
        }
        return ContainerEdit(
            container = output,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin"),
        )
    }
}
''',
        encoding="utf-8",
    )

    print("Golden D1 style0-only clean-plate/layout patch applied")


if __name__ == "__main__":
    main()
