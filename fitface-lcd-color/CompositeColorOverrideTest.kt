package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CompositeColorOverrideTest {
    @Test
    fun compositeRecolorsOnlyTheProvenPlus58ColorWord() {
        // A real type-13 record is 100 bytes = 36-byte head + 16 words. The watchface
        // format evidence pins the theme color to record +0x58, i.e. words[13]. Put a
        // second opaque-looking word earlier in the record so a generic "find an ARGB"
        // heuristic cannot accidentally pass this test.
        val words = listOf(
            0xFFFF0015L, 0x0006FFFFL, 0x00000001L,
            0xFFFF0000L, 0x0005FFFFL, 0xFF112233L,
            0xFFFF0012L, 0x0006FFFFL, 0x00000001L,
            0xFFFF0000L, 0xFFFFFFFFL, 0x00000000L,
            0xFFFFFFFFL, 0xFFD6E1F9L, 0x00010000L, 0x00080000L,
        )
        val source = syntheticContainer(words)
        val beforeEntry = source.entryByBasename("style0.bin")
        val beforeRecord = FaceRecordParser.scanWidgets(beforeEntry).single()
        val beforeWords = beforeRecord.words.toList()

        val edit = FaceEditor.recolorCompositeWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style0.bin"),
            globalIndex = beforeRecord.globalIndex,
            sequenceId = beforeRecord.sequenceId,
            x = beforeRecord.x,
            y = beforeRecord.y,
            colorArgb = 0xFFAEB4B2.toInt(),
        )

        val afterEntry = edit.container.entryByBasename("style0.bin")
        val afterRecord = FaceRecordParser.scanWidgets(afterEntry).single()

        beforeWords.indices.forEach { index ->
            val expected = if (index == 13) 0xFFAEB4B2L else beforeWords[index]
            assertEquals("word $index", expected, afterRecord.words[index])
        }
        assertEquals(beforeRecord.x, afterRecord.x)
        assertEquals(beforeRecord.y, afterRecord.y)
        assertEquals(beforeRecord.width, afterRecord.width)
        assertEquals(beforeRecord.height, afterRecord.height)
        assertEquals(source.fileSize, edit.container.fileSize)
        assertEquals(listOf("style0.bin"), edit.changedStyles)
        assertTrue(edit.container.validate().isValid)
    }

    @Test(expected = Fit3FormatException::class)
    fun compositeWithoutOpaquePlus58ColorIsRejected() {
        val words = MutableList(16) { 0L }
        words[13] = 0x00010203L
        val source = syntheticContainer(words)
        val record = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin")).single()
        FaceEditor.recolorCompositeWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style0.bin"),
            globalIndex = record.globalIndex,
            sequenceId = record.sequenceId,
            x = record.x,
            y = record.y,
            colorArgb = 0xFFAEB4B2.toInt(),
        )
    }

    private fun syntheticContainer(words: List<Long>): Fit3Container {
        val widgetSize = WIDGET_FIXED_SIZE + words.size * 4
        val styleSize = STYLE_HEADER_SIZE + widgetSize
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
        bytes.putU32(style + 0x14, STYLE_HEADER_SIZE + widgetSize)

        val widget = style + STYLE_HEADER_SIZE
        bytes.putU32(widget + 0x00, WIDGET_COMP)
        bytes.putU32(widget + 0x04, 0)
        bytes.putU32(widget + 0x08, 0)
        bytes.putU32(widget + 0x0C, (2 shl 16) or widgetSize)
        bytes.putU32(widget + 0x10, 0)
        bytes.putU32(widget + 0x14, 0)
        bytes.putU16(widget + 0x18, 134)
        bytes.putU16(widget + 0x1A, 68)
        bytes.putU16(widget + 0x1C, 120)
        bytes.putU16(widget + 0x1E, 42)
        bytes.putU32(widget + 0x20, 0)
        words.forEachIndexed { index, word ->
            bytes.putU32(widget + WIDGET_FIXED_SIZE + index * 4, word)
        }

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }
}
