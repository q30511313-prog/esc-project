package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PairBindingOverrideTest {
    @Test
    fun pairBindingIndexCanBeChangedWithoutTouchingLayoutBitsOrGeometry() {
        val source = syntheticContainer(bindingIndex = 7)
        val before = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin")).single()
        val beforeLayoutWord = before.words[1]

        val edit = FaceEditor.overridePairBindingAcrossStyles(
            source = source,
            entryBasenames = listOf("style0.bin"),
            globalIndex = before.globalIndex,
            sequenceId = before.sequenceId,
            x = before.x,
            y = before.y,
            newBindingIndex = 3,
        )
        val after = FaceRecordParser.scanWidgets(
            edit.container.entryByBasename("style0.bin"),
        ).single()

        assertEquals(3, (after.words[1] and 0xFF).toInt())
        assertEquals(beforeLayoutWord and 0xFFFF_FF00L, after.words[1] and 0xFFFF_FF00L)
        assertEquals(before.sequenceId, after.sequenceId)
        assertEquals(before.x, after.x)
        assertEquals(before.y, after.y)
        assertEquals(before.width, after.width)
        assertEquals(before.height, after.height)
        assertEquals(source.fileSize, edit.container.fileSize)
        assertEquals(listOf("style0.bin"), edit.changedStyles)
        assertTrue(edit.container.validate().isValid)
    }

    @Test(expected = Fit3FormatException::class)
    fun pairBindingOverrideRefusesPairWithoutBindingWord() {
        val source = syntheticContainer(bindingIndex = null)
        val before = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin")).single()
        FaceEditor.overridePairBindingAcrossStyles(
            source = source,
            entryBasenames = listOf("style0.bin"),
            globalIndex = before.globalIndex,
            sequenceId = before.sequenceId,
            x = before.x,
            y = before.y,
            newBindingIndex = 3,
        )
    }

    private fun syntheticContainer(bindingIndex: Int?): Fit3Container {
        val styleHeaderSize = STYLE_HEADER_SIZE
        val words = if (bindingIndex == null) 0 else 2
        val widgetSize = WIDGET_FIXED_SIZE + words * 4
        val styleSize = styleHeaderSize + widgetSize
        val bodyOffset = CONTAINER_HEADER_SIZE + DIRECTORY_ENTRY_SIZE
        val bytes = ByteArray(bodyOffset + styleSize)

        "oppo".toByteArray(StandardCharsets.US_ASCII).copyInto(bytes, 0)
        bytes.putU32(0x04, 4)
        bytes.putU32(0x08, bytes.size - CONTAINER_HEADER_SIZE)
        bytes.putU32(0x0C, 1)

        val directory = CONTAINER_HEADER_SIZE
        val path = "./SM-R390_00003_256x402/style0.bin".toByteArray(StandardCharsets.UTF_8)
        path.copyInto(bytes, directory)
        bytes.putU32(directory + 0x40, bodyOffset)
        bytes.putU32(directory + 0x44, styleSize)

        val style = bodyOffset
        bytes.putU32(style + 0x00, STYLE_MAGIC)
        bytes.putU32(style + 0x04, 1)
        bytes.putU32(style + 0x08, widgetSize)
        bytes.putU32(style + 0x0C, 0)
        bytes.putU32(style + 0x10, 0)
        bytes.putU32(style + 0x14, styleHeaderSize + widgetSize)

        val widget = style + styleHeaderSize
        bytes.putU32(widget + 0x00, WIDGET_PAIR)
        bytes.putU32(widget + 0x04, 37)
        bytes.putU32(widget + 0x08, 0)
        bytes.putU32(widget + 0x0C, (1 shl 16) or widgetSize)
        bytes.putU32(widget + 0x10, 0)
        bytes.putU32(widget + 0x14, 0)
        bytes.putU16(widget + 0x18, 17)
        bytes.putU16(widget + 0x1A, 68)
        bytes.putU16(widget + 0x1C, 65)
        bytes.putU16(widget + 0x1E, 42)
        bytes.putU32(widget + 0x20, 0)
        if (bindingIndex != null) {
            bytes.putU32(widget + WIDGET_FIXED_SIZE, 0xFFFFFFFFL)
            val layoutWord = 0xA1B2C300L or bindingIndex.toLong()
            bytes.putU32(widget + WIDGET_FIXED_SIZE + 4, layoutWord)
        }

        bytes.putU16(
            directory + 0x48,
            Crc16.ccittFalse(bytes, bodyOffset, bytes.size),
        )
        bytes.putU16(
            0x10,
            Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size),
        )
        val parsed = Fit3Container.parse(bytes)
        assertTrue(parsed.validate().isValid)
        return parsed
    }
}
