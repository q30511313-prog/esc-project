package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class StaticAlphaMaskTintTest {
    @Test
    fun blackRgbStaticMaskUsesAlphaCoverageAndKeepsAlphaBytes() {
        val source = syntheticStaticMaskContainer()
        val beforeEntry = source.entryByBasename("style3.bin")
        val beforeWidget = FaceRecordParser.scanWidgets(beforeEntry).single()
        val beforeImage = FaceRecordParser.scanImages(beforeEntry).single()
        val beforeBytes = source.toByteArray()

        val edit = FaceEditor.recolorStaticWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style3.bin"),
            globalIndex = beforeWidget.globalIndex,
            sequenceId = beforeWidget.sequenceId,
            x = beforeWidget.x,
            y = beforeWidget.y,
            red = 0xB8,
            green = 0xB8,
            blue = 0xAD,
        )

        val afterEntry = edit.container.entryByBasename("style3.bin")
        val afterImage = FaceRecordParser.scanImages(afterEntry).single()
        val afterBytes = edit.container.toByteArray()
        val before = beforeEntry.offset + beforeImage.samplesOffset
        val after = afterEntry.offset + afterImage.samplesOffset

        // Visible black RGB565+A mask pixel must receive the requested LCD RGB.
        assertEquals(0x0000, beforeBytes.u16(before))
        assertEquals(0xB5B5, afterBytes.u16(after))
        assertEquals(0x80, beforeBytes[before + 2].toInt() and 0xFF)
        assertEquals(0x80, afterBytes[after + 2].toInt() and 0xFF)

        // Fully transparent mask pixel stays byte-identical, including its black RGB.
        assertEquals(0x0000, beforeBytes.u16(before + 3))
        assertEquals(0x0000, afterBytes.u16(after + 3))
        assertEquals(0x00, afterBytes[after + 5].toInt() and 0xFF)

        assertEquals(source.fileSize, edit.container.fileSize)
        assertTrue(edit.container.validate().isValid)
    }

    private fun syntheticStaticMaskContainer(): Fit3Container {
        val widgetSize = 40
        val imageDataSize = 2 * 1 * 3
        val imageRecordSize = IMAGE_HEADER_SIZE + imageDataSize
        val styleSize = STYLE_HEADER_SIZE + widgetSize + imageRecordSize
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
        bytes.putU32(style + 0x04, 1)
        bytes.putU32(style + 0x08, widgetSize)
        bytes.putU32(style + 0x0C, imageRecordSize)
        bytes.putU32(style + 0x10, 0)
        bytes.putU32(style + 0x14, STYLE_HEADER_SIZE + widgetSize)

        val widget = style + STYLE_HEADER_SIZE
        bytes.putU32(widget + 0x00, WIDGET_STATIC)
        bytes.putU32(widget + 0x04, 0)
        bytes.putU32(widget + 0x08, 0)
        bytes.putU32(widget + 0x0C, (5 shl 16) or widgetSize)
        bytes.putU32(widget + 0x10, 0)
        bytes.putU32(widget + 0x14, 0)
        bytes.putU16(widget + 0x18, 73)
        bytes.putU16(widget + 0x1A, 166)
        bytes.putU16(widget + 0x1C, 20)
        bytes.putU16(widget + 0x1E, 68)
        bytes.putU32(widget + 0x20, 0)
        bytes.putU32(widget + 0x24, 0)

        val image = style + STYLE_HEADER_SIZE + widgetSize
        bytes.putU16(image + 0x00, 2)
        bytes.putU16(image + 0x02, 1)
        bytes.putU16(image + 0x04, IMAGE_RGB565_ALPHA)
        bytes.putU16(image + 0x06, 0)
        bytes.putU32(image + 0x08, imageDataSize)

        val samples = image + IMAGE_HEADER_SIZE
        bytes.putU16(samples + 0, 0x0000)
        bytes[samples + 2] = 0x80.toByte()
        bytes.putU16(samples + 3, 0x0000)
        bytes[samples + 5] = 0x00

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }
}
