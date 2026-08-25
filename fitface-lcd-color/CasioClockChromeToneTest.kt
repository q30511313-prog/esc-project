package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CasioClockChromeToneTest {
    @Test
    fun clockRecolorAlsoTintsSharedColonsAndOnlyStyle3SeparatorLines() {
        val source = syntheticSamsung00003Style3()
        val beforeEntry = source.entryByBasename("style3.bin")
        val beforeRecords = FaceRecordParser.scanWidgets(beforeEntry)
        val hourUnits = beforeRecords.single { it.widgetType == WIDGET_SPRITE && it.sequenceId == 3 }
        val beforeImages = FaceRecordParser.scanImages(beforeEntry)
        val beforeBytes = source.toByteArray()

        val edit = FaceEditor.recolorSpriteWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style3.bin"),
            globalIndex = hourUnits.globalIndex,
            sequenceId = hourUnits.sequenceId,
            x = hourUnits.x,
            y = hourUnits.y,
            red = 0xB8,
            green = 0xB8,
            blue = 0xAD,
        )

        val afterEntry = edit.container.entryByBasename("style3.bin")
        val afterImages = FaceRecordParser.scanImages(afterEntry)
        val afterBytes = edit.container.toByteArray()

        val backgroundBefore = beforeEntry.offset + beforeImages[0].samplesOffset
        val backgroundAfter = afterEntry.offset + afterImages[0].samplesOffset
        val digitBefore = beforeEntry.offset + beforeImages[1].samplesOffset
        val digitAfter = afterEntry.offset + afterImages[1].samplesOffset
        val colonBefore = beforeEntry.offset + beforeImages[2].samplesOffset
        val colonAfter = afterEntry.offset + afterImages[2].samplesOffset

        // Digital clock glyph pool receives the requested LCD gray.
        assertEquals(0xFFFF, beforeBytes.u16(digitBefore))
        assertEquals(0xB5B5, afterBytes.u16(digitAfter))

        // Both colon widgets share image #2. The same clock action must bring that
        // shared raster onto the identical neutral LCD color axis.
        assertEquals(0xFFFF, beforeBytes.u16(colonBefore))
        assertEquals(0xB5B5, afterBytes.u16(colonAfter))

        // The three separator bars are baked into style3 background image #0.
        // They keep their stored luminance/AA while their hue is moved to the
        // requested neutral LCD axis.
        val topLeft = pixelOffset(14, 133)
        val topRight = pixelOffset(139, 133)
        val bottom = pixelOffset(14, 264)
        val expectedLine = SpriteTint.tintRgb565(0x4A49, 0xB8, 0xB8, 0xAD)
        for (offset in intArrayOf(topLeft, topRight, bottom)) {
            assertEquals(0x4A49, beforeBytes.u16(backgroundBefore + offset))
            assertEquals(expectedLine, afterBytes.u16(backgroundAfter + offset))
            assertNotEquals(0x4A49, afterBytes.u16(backgroundAfter + offset))
            // RGB565+A background alpha byte is structural and must stay untouched.
            assertEquals(0xFF, beforeBytes[backgroundBefore + offset + 2].toInt() and 0xFF)
            assertEquals(0xFF, afterBytes[backgroundAfter + offset + 2].toInt() and 0xFF)
        }

        // Full-panel tinting is forbidden: unrelated colored pixels and black panel
        // pixels outside the three proven separator rectangles remain byte-identical.
        val unrelated = pixelOffset(10, 10)
        assertEquals(0xF800, beforeBytes.u16(backgroundBefore + unrelated))
        assertEquals(0xF800, afterBytes.u16(backgroundAfter + unrelated))
        val black = pixelOffset(5, 200)
        assertEquals(0x0000, beforeBytes.u16(backgroundBefore + black))
        assertEquals(0x0000, afterBytes.u16(backgroundAfter + black))

        assertEquals(source.fileSize, edit.container.fileSize)
        assertEquals(listOf("style3.bin"), edit.changedStyles)
        assertTrue(edit.container.validate().isValid)
    }

    private fun pixelOffset(x: Int, y: Int): Int = (y * 256 + x) * 3

    private fun syntheticSamsung00003Style3(): Fit3Container {
        val spriteSequences = listOf(2, 3, 10, 11, 14, 15)
        val spriteX = listOf(0, 37, 90, 127, 180, 218)
        val spriteRecordSize = WIDGET_FIXED_SIZE + 4
        val staticRecordSize = 40
        val widgetCount = 1 + spriteSequences.size + 2
        val widgetBytes = staticRecordSize + spriteSequences.size * spriteRecordSize + 2 * staticRecordSize

        val backgroundSamples = 256 * 402 * 3
        val backgroundRecordSize = IMAGE_HEADER_SIZE + backgroundSamples
        val digitRecordSize = IMAGE_HEADER_SIZE + 2
        val colonRecordSize = IMAGE_HEADER_SIZE + 2
        val imageBytes = backgroundRecordSize + digitRecordSize + colonRecordSize
        val styleSize = STYLE_HEADER_SIZE + widgetBytes + imageBytes
        val bodyOffset = CONTAINER_HEADER_SIZE + DIRECTORY_ENTRY_SIZE
        val bytes = ByteArray(bodyOffset + styleSize)

        "oppo".toByteArray(StandardCharsets.US_ASCII).copyInto(bytes, 0)
        bytes.putU32(0x04, 4)
        bytes.putU32(0x08, bytes.size - CONTAINER_HEADER_SIZE)
        bytes.putU32(0x0C, 1)

        val directory = CONTAINER_HEADER_SIZE
        val path = "./SM-R390_00003_256x402/style3.bin".toByteArray(StandardCharsets.UTF_8)
        path.copyInto(bytes, directory)
        bytes.putU32(directory + 0x40, bodyOffset)
        bytes.putU32(directory + 0x44, styleSize)

        val style = bodyOffset
        bytes.putU32(style + 0x00, STYLE_MAGIC)
        bytes.putU32(style + 0x04, widgetCount)
        bytes.putU32(style + 0x08, widgetBytes)
        bytes.putU32(style + 0x0C, imageBytes)
        bytes.putU32(style + 0x10, 0)
        bytes.putU32(style + 0x14, STYLE_HEADER_SIZE + widgetBytes)

        var cursor = style + STYLE_HEADER_SIZE
        fun writeStatic(globalIndex: Int, x: Int, y: Int, relativeImageOffset: Int) {
            bytes.putU32(cursor + 0x00, WIDGET_STATIC)
            bytes.putU32(cursor + 0x04, 0)
            bytes.putU32(cursor + 0x08, 0)
            bytes.putU32(cursor + 0x0C, (globalIndex shl 16) or staticRecordSize)
            bytes.putU32(cursor + 0x10, 0)
            bytes.putU32(cursor + 0x14, 0)
            bytes.putU16(cursor + 0x18, x)
            bytes.putU16(cursor + 0x1A, y)
            bytes.putU16(cursor + 0x1C, if (x == 0 && y == 0) 256 else 20)
            bytes.putU16(cursor + 0x1E, if (x == 0 && y == 0) 402 else 68)
            bytes.putU32(cursor + 0x20, relativeImageOffset)
            bytes.putU32(cursor + 0x24, 0)
            cursor += staticRecordSize
        }

        writeStatic(globalIndex = 0, x = 0, y = 0, relativeImageOffset = 0)

        val digitRelativeOffset = backgroundRecordSize
        spriteSequences.forEachIndexed { index, sequenceId ->
            bytes.putU32(cursor + 0x00, WIDGET_SPRITE)
            bytes.putU32(cursor + 0x04, sequenceId)
            bytes.putU32(cursor + 0x08, 0)
            bytes.putU32(cursor + 0x0C, ((index + 1) shl 16) or spriteRecordSize)
            bytes.putU32(cursor + 0x10, 0)
            bytes.putU32(cursor + 0x14, 0)
            bytes.putU16(cursor + 0x18, spriteX[index])
            bytes.putU16(cursor + 0x1A, 166)
            bytes.putU16(cursor + 0x1C, 1)
            bytes.putU16(cursor + 0x1E, 1)
            bytes.putU32(cursor + 0x20, 1)
            bytes.putU32(cursor + WIDGET_FIXED_SIZE, digitRelativeOffset)
            cursor += spriteRecordSize
        }

        val colonRelativeOffset = backgroundRecordSize + digitRecordSize
        writeStatic(globalIndex = 7, x = 73, y = 166, relativeImageOffset = colonRelativeOffset)
        writeStatic(globalIndex = 8, x = 162, y = 166, relativeImageOffset = colonRelativeOffset)

        val imageSection = style + STYLE_HEADER_SIZE + widgetBytes
        // image #0: full-panel RGB565+A, matching Samsung 00003 style3.
        bytes.putU16(imageSection + 0x00, 256)
        bytes.putU16(imageSection + 0x02, 402)
        bytes.putU16(imageSection + 0x04, IMAGE_RGB565_ALPHA)
        bytes.putU16(imageSection + 0x06, 0)
        bytes.putU32(imageSection + 0x08, backgroundSamples)
        val bg = imageSection + IMAGE_HEADER_SIZE
        repeat(256 * 402) { pixel ->
            bytes.putU16(bg + pixel * 3, 0x0000)
            bytes[bg + pixel * 3 + 2] = 0xFF.toByte()
        }
        // One unrelated color proves the implementation does not tint the whole panel.
        bytes.putU16(bg + pixelOffset(10, 10), 0xF800)
        val separatorRects = listOf(
            intArrayOf(14, 120, 133, 134),
            intArrayOf(139, 245, 133, 134),
            intArrayOf(14, 241, 264, 265),
        )
        separatorRects.forEach { rect ->
            for (y in rect[2]..rect[3]) {
                for (x in rect[0]..rect[1]) {
                    bytes.putU16(bg + pixelOffset(x, y), 0x4A49)
                }
            }
        }

        // image #1: one-pixel shared digit pool.
        val digit = imageSection + backgroundRecordSize
        bytes.putU16(digit + 0x00, 1)
        bytes.putU16(digit + 0x02, 1)
        bytes.putU16(digit + 0x04, IMAGE_RGB565)
        bytes.putU16(digit + 0x06, 0)
        bytes.putU32(digit + 0x08, 2)
        bytes.putU16(digit + IMAGE_HEADER_SIZE, 0xFFFF)

        // image #2: one-pixel raster shared by both colon Static widgets.
        val colon = digit + digitRecordSize
        bytes.putU16(colon + 0x00, 1)
        bytes.putU16(colon + 0x02, 1)
        bytes.putU16(colon + 0x04, IMAGE_RGB565)
        bytes.putU16(colon + 0x06, 0)
        bytes.putU32(colon + 0x08, 2)
        bytes.putU16(colon + IMAGE_HEADER_SIZE, 0xFFFF)

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }
}
