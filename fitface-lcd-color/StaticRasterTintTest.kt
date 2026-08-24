package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class StaticRasterTintTest {
    @Test
    fun staticRasterPixelsAreTintedWithoutChangingGeometryOrAlpha() {
        val source = syntheticStaticContainer()
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
            red = 0xAE,
            green = 0xB4,
            blue = 0xB2,
        )

        val afterEntry = edit.container.entryByBasename("style3.bin")
        val afterWidget = FaceRecordParser.scanWidgets(afterEntry).single()
        val afterImage = FaceRecordParser.scanImages(afterEntry).single()
        val afterBytes = edit.container.toByteArray()

        assertEquals(beforeWidget, afterWidget)
        assertEquals(beforeImage.width, afterImage.width)
        assertEquals(beforeImage.height, afterImage.height)
        assertEquals(beforeImage.format, afterImage.format)
        assertEquals(source.fileSize, edit.container.fileSize)
        assertEquals(listOf("style3.bin"), edit.changedStyles)
        assertTrue(edit.container.validate().isValid)

        val beforeAbsolute = beforeEntry.offset + beforeImage.samplesOffset
        val afterAbsolute = afterEntry.offset + afterImage.samplesOffset
        val beforeMagenta = beforeBytes.u16(beforeAbsolute)
        val afterSilver = afterBytes.u16(afterAbsolute)
        assertEquals(0xF81F, beforeMagenta)
        assertNotEquals(beforeMagenta, afterSilver)
        // Second pixel is black and must remain black.
        assertEquals(0x0000, afterBytes.u16(afterAbsolute + 2))
    }

    private fun syntheticStaticContainer(): Fit3Container {
        val widgetSize = 40
        val imageDataSize = 2 * 2 * 2 + 4
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
        bytes.putU32(widget + 0x20, 0) // first image, relative to image section
        bytes.putU32(widget + 0x24, 0)

        val image = style + STYLE_HEADER_SIZE + widgetSize
        bytes.putU16(image + 0x00, 2)
        bytes.putU16(image + 0x02, 2)
        bytes.putU16(image + 0x04, IMAGE_RGB565)
        bytes.putU16(image + 0x06, 0)
        bytes.putU32(image + 0x08, imageDataSize)
        bytes.putU16(image + IMAGE_HEADER_SIZE + 0, 0xF81F)
        bytes.putU16(image + IMAGE_HEADER_SIZE + 2, 0x0000)
        bytes.putU16(image + IMAGE_HEADER_SIZE + 4, 0xFFFF)
        bytes.putU16(image + IMAGE_HEADER_SIZE + 6, 0x8410)
        // four-byte trailer remains zero

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }
}
