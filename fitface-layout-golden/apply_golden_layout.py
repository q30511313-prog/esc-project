#!/usr/bin/env python3
"""Install the style0-only Golden D1 clean-plate/layout compiler into FitFace.

The patch is fail-closed against the pinned upstream FaceEditor shape. It adds a
single-style background rewrite rather than calling the existing all-style helper,
then writes GoldenD1LayoutCompiler.kt which composes that rewrite with the already
proven GoldenD1Compiler semantic transaction.

The approved clean plate is stored as text-safe zlib/base64 chunks. The patch
verifies the assembled RGB565 payload before emitting GoldenD1CleanPlate.kt; runtime
code verifies it again before exposing ARGB pixels to the style0 background writer.
"""
from pathlib import Path
import base64
import hashlib
import json
import sys
import zlib

RAW_RGB565_BYTES = 205824
RAW_RGB565_SHA256 = "e12a722dc7a1e51bde71c9ffa375e0ec9443521e9da9feaef77819ee8e939c3e"
PART_NAMES = [
    "golden_d1_clean_plate_rgb565.zlib.b64.part00",
    "golden_d1_clean_plate_rgb565.zlib.b64.part01",
    "golden_d1_clean_plate_rgb565.zlib.b64.part02a",
    "golden_d1_clean_plate_rgb565.zlib.b64.part02b",
    "golden_d1_clean_plate_rgb565.zlib.b64.part02c",
    "golden_d1_clean_plate_rgb565.zlib.b64.part03",
]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def load_approved_payload_parts(helper_dir: Path) -> list[str]:
    parts: list[str] = []
    for name in PART_NAMES:
        path = helper_dir / name
        if not path.is_file():
            raise SystemExit(f"approved Golden D1 payload part missing: {name}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"approved Golden D1 payload part empty: {name}")
        parts.append(text)

    try:
        packed = base64.b64decode("".join(parts), validate=True)
        raw = zlib.decompress(packed)
    except Exception as error:
        raise SystemExit(f"approved Golden D1 payload decode failed: {error}") from error

    if len(raw) != RAW_RGB565_BYTES:
        raise SystemExit(
            f"approved Golden D1 RGB565 length drifted: {len(raw)} != {RAW_RGB565_BYTES}",
        )
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RAW_RGB565_SHA256:
        raise SystemExit(
            f"approved Golden D1 RGB565 SHA-256 drifted: {digest} != {RAW_RGB565_SHA256}",
        )
    return parts


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_layout.py FITFACE_ROOT")

    helper_dir = Path(__file__).resolve().parent
    payload_parts = load_approved_payload_parts(helper_dir)
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

    plate = root / (
        "core/format/src/main/kotlin/dev/fitface/studio/core/format/"
        "GoldenD1CleanPlate.kt"
    )
    kotlin_parts = ",\n        ".join(json.dumps(part) for part in payload_parts)
    plate_template = '''package dev.fitface.studio.core.format

import java.io.ByteArrayInputStream
import java.security.MessageDigest
import java.util.Base64
import java.util.zip.InflaterInputStream

/** Exact RGB565 clean plate derived deterministically from approved 1000028944.png. */
object GoldenD1CleanPlate {
    const val WIDTH = 256
    const val HEIGHT = 402
    const val RAW_RGB565_BYTES = 205824
    const val RAW_RGB565_SHA256 = "e12a722dc7a1e51bde71c9ffa375e0ec9443521e9da9feaef77819ee8e939c3e"

    private val PAYLOAD = listOf(
        __PAYLOAD_PARTS__
    ).joinToString("")

    fun argb(): IntArray {
        val packed = try {
            Base64.getDecoder().decode(PAYLOAD)
        } catch (error: IllegalArgumentException) {
            throw Fit3FormatException("Golden D1 clean-plate base64 is invalid")
        }
        val raw = try {
            InflaterInputStream(ByteArrayInputStream(packed)).use { it.readBytes() }
        } catch (error: Exception) {
            throw Fit3FormatException("Golden D1 clean-plate zlib decode failed")
        }
        if (raw.size != RAW_RGB565_BYTES) {
            throw Fit3FormatException(
                "Golden D1 clean-plate RGB565 length drifted: ${raw.size} != $RAW_RGB565_BYTES",
            )
        }
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(raw)
            .joinToString("") { byte -> "%02x".format(byte.toInt() and 0xFF) }
        if (digest != RAW_RGB565_SHA256) {
            throw Fit3FormatException("Golden D1 clean-plate RGB565 SHA-256 mismatch")
        }

        return IntArray(WIDTH * HEIGHT) { index ->
            val offset = index * 2
            val rgb565 = (raw[offset].toInt() and 0xFF) or
                ((raw[offset + 1].toInt() and 0xFF) shl 8)
            val r5 = (rgb565 ushr 11) and 0x1F
            val g6 = (rgb565 ushr 5) and 0x3F
            val b5 = rgb565 and 0x1F
            val red = (r5 shl 3) or (r5 ushr 2)
            val green = (g6 shl 2) or (g6 ushr 4)
            val blue = (b5 shl 3) or (b5 ushr 2)
            (0xFF shl 24) or (red shl 16) or (green shl 8) or blue
        }
    }
}
'''
    plate.write_text(
        plate_template.replace("__PAYLOAD_PARTS__", kotlin_parts),
        encoding="utf-8",
    )

    compiler = root / (
        "core/format/src/main/kotlin/dev/fitface/studio/core/format/"
        "GoldenD1LayoutCompiler.kt"
    )
    compiler.write_text(
        '''package dev.fitface.studio.core.format

/**
 * Task-7 Golden assembler. Replaces only style0's full-panel background with the
 * approved 256x402 clean plate, then applies the already-proven D1 live semantic
 * compiler. Sibling style payloads are asserted byte-identical.
 */
object GoldenD1LayoutCompiler {
    const val WIDTH = 256
    const val HEIGHT = 402

    fun compile(source: Fit3Container): ContainerEdit =
        compile(source, GoldenD1CleanPlate.argb())

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
    print(f"Golden D1 embedded RGB565 SHA256={RAW_RGB565_SHA256}")


if __name__ == "__main__":
    main()
