package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AnchoredPairColorTest {
    @Test
    fun rightAnchoredPairRecolorsEvenWhenUiXIsDisplayCoordinate() {
        val source = syntheticPairContainer()
        val before = FaceRecordParser.scanWidgets(source.entryByBasename("style3.bin")).single()
        assertEquals(-174, before.x)
        assertEquals(0xFFD6E1F9L, before.words[0])

        // The editor displays this right-anchored record at X=17 on the 256 px panel.
        // Color selection must identify the widget by its stable record identity rather
        // than comparing that display X against the stored -174 anchor coordinate.
        val edit = FaceEditor.recolorPairWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style3.bin"),
            globalIndex = before.globalIndex,
            sequenceId = before.sequenceId,
            x = 17,
            y = 68,
            colorArgb = 0xFF9F9E99.toInt(),
        )
        val after = FaceRecordParser.scanWidgets(edit.container.entryByBasename("style3.bin")).single()
        assertEquals(-174, after.x)
        assertEquals(68, after.y)
        assertEquals(0xFF9F9E99L, after.words[0])
        assertTrue(edit.container.validate().isValid)
    }

    private fun syntheticPairContainer(): Fit3Container {
        val words = listOf(0xFFD6E1F9L, 0x01000001L, 0x0001FFFFL, 0L, 0L)
        val widgetSize = WIDGET_FIXED_SIZE + words.size * 4
        val styleSize = STYLE_HEADER_SIZE + widgetSize
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
        bytes.putU32(style + 0x0C, 0)
        bytes.putU32(style + 0x10, 0)
        bytes.putU32(style + 0x14, STYLE_HEADER_SIZE + widgetSize)

        val widget = style + STYLE_HEADER_SIZE
        bytes.putU32(widget + 0x00, WIDGET_PAIR)
        bytes.putU32(widget + 0x04, 37)
        bytes.putU32(widget + 0x08, 0)
        bytes.putU32(widget + 0x0C, (1 shl 16) or widgetSize)
        bytes.putU32(widget + 0x10, 0)
        bytes.putU32(widget + 0x14, 0)
        bytes.putU16(widget + 0x18, (-174) and 0xFFFF)
        bytes.putU16(widget + 0x1A, 68)
        bytes.putU16(widget + 0x1C, 65)
        bytes.putU16(widget + 0x1E, 42)
        bytes.putU32(widget + 0x20, 3)
        words.forEachIndexed { index, word -> bytes.putU32(widget + WIDGET_FIXED_SIZE + index * 4, word) }

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }
}
