#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

old = '''                    // RGB565+A alpha byte, when present, remains verbatim.
                }
            }
            if (entryChanged > 0) {
'''
new = '''                    // RGB565+A alpha byte, when present, remains verbatim.
                }
            }
            // Samsung 00003's digital clock is split across three storage paths:
            // Sprite glyphs, two shared Static colon rasters, and three separator
            // bars baked into style3 background image #0. Once the proven six-Sprite
            // clock signature is present, keep those pieces on one neutral LCD axis.
            // The face/path gate and exact raster signature prevent this from becoming
            // a generic background-coordinate rewrite on unrelated faces.
            if (
                clockSprites != null &&
                entry.path.contains("/SM-R390_00003_256x402/")
            ) {
                entryChanged += tintSamsung00003CasioClockChrome(
                    entry = entry,
                    records = records,
                    images = images,
                    output = output,
                    red = red,
                    green = green,
                    blue = blue,
                )
            }
            if (entryChanged > 0) {
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one Sprite tail anchor, found {count}")
text = text.replace(old, new, 1)

anchor = '''    fun replaceBackgrounds(
'''
helper = '''    private fun tintSamsung00003CasioClockChrome(
        entry: ContainerEntry,
        records: List<WidgetRecord>,
        images: List<ImageRecord>,
        output: ByteArray,
        red: Int,
        green: Int,
        blue: Int,
    ): Int {
        val firstImageOffset = images.firstOrNull()?.recordOffset ?: return 0
        val imagesByRelativeOffset = images.associateBy {
            (it.recordOffset - firstImageOffset).toLong()
        }

        // Both ':' widgets are TYPE-1 Static records and intentionally share the
        // same raster. Resolve both positions and require exactly one shared image
        // before touching it; a changed schema is left alone rather than guessed at.
        val colonWidgets = listOf(73, 162).map { colonX ->
            records.singleOrNull {
                it.widgetType == WIDGET_STATIC &&
                    it.sequenceId == 0 &&
                    it.x == colonX &&
                    it.y == 166
            } ?: return 0
        }
        val colonImages = colonWidgets.mapNotNull { widget ->
            imagesByRelativeOffset[widget.unknown20]
        }.distinctBy { it.recordOffset }
        if (colonImages.size != 1) return 0
        val colonImage = colonImages.single()
        if (colonImage.format !in setOf(IMAGE_RGB565, IMAGE_RGB565_ALPHA)) return 0

        var changed = 0
        fun writeRgb565(absolute: Int, replacement: Int) {
            val low = replacement.toByte()
            val high = (replacement ushr 8).toByte()
            if (output[absolute] != low) changed++
            if (output[absolute + 1] != high) changed++
            output[absolute] = low
            output[absolute + 1] = high
        }

        repeat(colonImage.width * colonImage.height) { pixel ->
            val absolute = entry.offset + colonImage.samplesOffset +
                pixel * colonImage.bytesPerPixel
            val existing = output.u16(absolute)
            val replacement = if (colonImage.format == IMAGE_RGB565_ALPHA) {
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
            if (replacement != existing) writeRgb565(absolute, replacement)
            // Alpha stays byte-identical for RGB565+A.
        }

        // Only the black style has the three separator bars baked into the panel
        // background. Diagnostics on the stock Samsung 00003 binary proved these
        // exact connected-component bounds: 107x2, 107x2, and 228x2 pixels.
        if (entry.basename != "style3.bin") return changed
        val background = FaceRecordParser.backgroundImage(entry) ?: return changed
        if (
            background.width != 256 ||
            background.height != 402 ||
            background.format != IMAGE_RGB565_ALPHA
        ) {
            return changed
        }

        val separatorRects = listOf(
            intArrayOf(14, 120, 133, 134),
            intArrayOf(139, 245, 133, 134),
            intArrayOf(14, 241, 264, 265),
        )
        val separatorAddresses = buildList {
            separatorRects.forEach { rect ->
                for (lineY in rect[2]..rect[3]) {
                    for (lineX in rect[0]..rect[1]) {
                        val pixel = lineY * background.width + lineX
                        add(
                            entry.offset + background.samplesOffset +
                                pixel * background.bytesPerPixel,
                        )
                    }
                }
            }
        }
        // The stock connected components occupy every pixel in those rectangles.
        // If any expected line pixel is black, the raster is no longer the proven
        // schema and the background portion of this patch is skipped safely.
        if (separatorAddresses.any { output.u16(it) == 0 }) return changed

        separatorAddresses.forEach { absolute ->
            val existing = output.u16(absolute)
            val replacement = SpriteTint.tintRgb565(existing, red, green, blue)
            if (replacement != existing) writeRgb565(absolute, replacement)
            // style3 background is RGB565+A; alpha is deliberately untouched.
        }
        return changed
    }

    fun replaceBackgrounds(
'''
count = text.count(anchor)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one helper insertion anchor, found {count}")
text = text.replace(anchor, helper, 1)

path.write_text(text)
print("Samsung 00003 Casio clock chrome tone fix applied")
