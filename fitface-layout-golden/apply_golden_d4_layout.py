#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import sys
import zlib

WIDTH = 256
HEIGHT = 402
RAW_BYTES = WIDTH * HEIGHT * 2
RAW_SHA256 = "7fe888c2f4536801c916cbdcf026cbad1392a0cd54ff6ad82b00ca2093a34db8"
PARTS = (
    "golden_d4_clean_plate_v2.b64.part1",
    "golden_d4_clean_plate_v2.b64.part2",
    "golden_d4_clean_plate_v2.b64.part3",
)


def fail(message: str) -> None:
    raise SystemExit(f"D4 clean plate: {message}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_golden_d4_layout.py <fitface-studio-root>")

    helper = Path(__file__).resolve().parent
    target_root = Path(sys.argv[1]).resolve()
    payload_text = "".join(
        "".join((helper / name).read_text(encoding="utf-8").split())
        for name in PARTS
    )
    try:
        compressed = base64.b64decode(payload_text, validate=True)
        raw = zlib.decompress(compressed)
    except Exception as error:
        fail(f"payload decode failed: {error}")

    if len(raw) != RAW_BYTES:
        fail(f"raw length {len(raw)}, expected {RAW_BYTES}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RAW_SHA256:
        fail(f"raw SHA256 {digest}, expected {RAW_SHA256}")

    kotlin_chunks = [payload_text[i : i + 1000] for i in range(0, len(payload_text), 1000)]
    payload_lines = "\n".join(f'        "{chunk}",' for chunk in kotlin_chunks)
    source = '''package dev.fitface.studio.core.format

import java.io.ByteArrayInputStream
import java.security.MessageDigest
import java.util.Base64
import java.util.zip.InflaterInputStream

/** Deterministic D4/style2 clean plate for approved artwork 1000028941. */
object GoldenD4CleanPlate {
    const val WIDTH = 256
    const val HEIGHT = 402
    const val RAW_BYTES = WIDTH * HEIGHT * 2
    const val RAW_SHA256 = "@SHA@"

    private val payloadBase64 = listOf(
@PAYLOAD@
    ).joinToString(separator = "")

    fun argb(): IntArray {
        val compressed = try {
            Base64.getDecoder().decode(payloadBase64)
        } catch (error: IllegalArgumentException) {
            throw Fit3FormatException("Golden D4 clean plate base64 is invalid", error)
        }
        val raw = try {
            InflaterInputStream(ByteArrayInputStream(compressed)).use { it.readBytes() }
        } catch (error: Exception) {
            throw Fit3FormatException("Golden D4 clean plate zlib payload is invalid", error)
        }
        if (raw.size != RAW_BYTES) {
            throw Fit3FormatException(
                "Golden D4 clean plate raw size ${raw.size}, expected $RAW_BYTES",
            )
        }
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(raw)
            .joinToString(separator = "") { "%02x".format(it) }
        if (digest != RAW_SHA256) {
            throw Fit3FormatException(
                "Golden D4 clean plate SHA256 $digest, expected $RAW_SHA256",
            )
        }

        return IntArray(WIDTH * HEIGHT) { index ->
            val offset = index * 2
            val rgb565 = (raw[offset].toInt() and 0xFF) or
                ((raw[offset + 1].toInt() and 0xFF) shl 8)
            val red = (((rgb565 ushr 11) and 0x1F) * 255 + 15) / 31
            val green = (((rgb565 ushr 5) and 0x3F) * 255 + 31) / 63
            val blue = ((rgb565 and 0x1F) * 255 + 15) / 31
            (0xFF shl 24) or (red shl 16) or (green shl 8) or blue
        }
    }
}
'''.replace("@SHA@", RAW_SHA256).replace("@PAYLOAD@", payload_lines)

    destination = target_root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/GoldenD4CleanPlate.kt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source, encoding="utf-8")
    print(f"D4_CLEAN_PLATE_RGB565_SHA256={digest}")
    print(f"D4_CLEAN_PLATE_RAW_BYTES={len(raw)}")
    print(f"D4_CLEAN_PLATE_KOTLIN={destination}")


if __name__ == "__main__":
    main()
