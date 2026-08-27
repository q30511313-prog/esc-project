#!/usr/bin/env python3
"""Install the exact embedded D2 RGB565 clean plate into a pinned FitFace workspace."""
from pathlib import Path
import base64
import hashlib
import json
import sys
import zlib

RAW_RGB565_BYTES = 205824
RAW_RGB565_SHA256 = "3718133cdd95f45155706222f5d402623aa62d0fe941b33d320090f26aa72b64"
PART_NAMES = [
    "golden_d2_clean_plate_rgb565.zlib.b64.part00",
    "golden_d2_clean_plate_rgb565.zlib.b64.part01",
    "golden_d2_clean_plate_rgb565.zlib.b64.part02",
    "golden_d2_clean_plate_rgb565.zlib.b64.part03",
]


def load_parts(helper_dir: Path) -> list[str]:
    parts = []
    for name in PART_NAMES:
        path = helper_dir / name
        if not path.is_file():
            raise SystemExit(f"Golden D2 payload part missing: {name}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"Golden D2 payload part empty: {name}")
        parts.append(text)
    try:
        raw = zlib.decompress(base64.b64decode("".join(parts), validate=True))
    except Exception as error:
        raise SystemExit(f"Golden D2 payload decode failed: {error}") from error
    if len(raw) != RAW_RGB565_BYTES:
        raise SystemExit(f"Golden D2 RGB565 length drifted: {len(raw)} != {RAW_RGB565_BYTES}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RAW_RGB565_SHA256:
        raise SystemExit(f"Golden D2 RGB565 SHA-256 drifted: {digest} != {RAW_RGB565_SHA256}")
    return parts


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_d2_layout.py FITFACE_ROOT")
    helper_dir = Path(__file__).resolve().parent
    parts = load_parts(helper_dir)
    root = Path(sys.argv[1]).resolve()
    target = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/GoldenD2CleanPlate.kt"
    kotlin_parts = ",\n        ".join(json.dumps(part) for part in parts)
    source = '''package dev.fitface.studio.core.format

import java.io.ByteArrayInputStream
import java.security.MessageDigest
import java.util.Base64
import java.util.zip.InflaterInputStream

/** Exact RGB565 clean plate derived from the approved D2 1000028943 artwork. */
object GoldenD2CleanPlate {
    const val WIDTH = 256
    const val HEIGHT = 402
    const val RAW_RGB565_BYTES = 205824
    const val RAW_RGB565_SHA256 = "3718133cdd95f45155706222f5d402623aa62d0fe941b33d320090f26aa72b64"

    private val PAYLOAD = listOf(
        __PARTS__
    ).joinToString("")

    fun argb(): IntArray {
        val packed = try {
            Base64.getDecoder().decode(PAYLOAD)
        } catch (error: IllegalArgumentException) {
            throw Fit3FormatException("Golden D2 clean-plate base64 is invalid")
        }
        val raw = try {
            InflaterInputStream(ByteArrayInputStream(packed)).use { it.readBytes() }
        } catch (error: Exception) {
            throw Fit3FormatException("Golden D2 clean-plate zlib decode failed")
        }
        if (raw.size != RAW_RGB565_BYTES) {
            throw Fit3FormatException("Golden D2 clean-plate RGB565 length drifted")
        }
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(raw)
            .joinToString("") { byte -> "%02x".format(byte.toInt() and 0xFF) }
        if (digest != RAW_RGB565_SHA256) {
            throw Fit3FormatException("Golden D2 clean-plate RGB565 SHA-256 mismatch")
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
'''.replace("__PARTS__", kotlin_parts)
    target.write_text(source, encoding="utf-8")
    print(f"Golden D2 embedded RGB565 SHA256={RAW_RGB565_SHA256}")


if __name__ == "__main__":
    main()
