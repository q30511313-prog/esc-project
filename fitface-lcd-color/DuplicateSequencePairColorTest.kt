package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DuplicateSequencePairColorTest {
    @Test
    fun valueColorsRemainEditableWhenSeveralValuesShareSequenceZero() {
        val source = syntheticContainer()
        val entry = source.entryByBasename("style3.bin")
        val guides = FaceRecordParser.widgetGuides(entry)

        val battery = guides.single { it.globalIndex == 17 }
        val neighbour = guides.single { it.globalIndex == 18 }

        assertEquals(WIDGET_PAIR, battery.type)
        assertEquals(0, battery.sequenceId)
        assertEquals(0, neighbour.sequenceId)
        assertNotNull(battery.colorArgb)
        assertNotNull(neighbour.colorArgb)
        assertEquals(0xFFFFFFFF.toInt(), battery.colorArgb)
        assertEquals(0xFFB2B2B2.toInt(), neighbour.colorArgb)
    }

    private fun syntheticContainer(): Fit3Container {
        val wordsA = listOf(0xFFFFFFFFL, 0x00010102L, 0x00020004L, 0L, 0L)
        val wordsB = listOf(0xFFB2B2B2L, 0x00000103L, 0x00030000L, 0L, 0L)
        val recordSize = WIDGET_FIXED_SIZE + wordsA.size * 4
        val widgetBytes = recordSize * 2
        val styleSize = STYLE_HEADER_SIZE + widgetBytes
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
        bytes.putU32(style + 0x04, 2)
        bytes.putU32(style + 0x08, widgetBytes)
        bytes.putU32(style + 0x0C, 0)
        bytes.putU32(style + 0x10, 0)
        bytes.putU32(style + 0x14, STYLE_HEADER_SIZE + widgetBytes)

        writePair(
            bytes = bytes,
            offset = style + STYLE_HEADER_SIZE,
            globalIndex = 17,
            x = 82,
            y = 82,
            width = 18,
            height = 23,
            words = wordsA,
        )
        writePair(
            bytes = bytes,
            offset = style + STYLE_HEADER_SIZE + recordSize,
            globalIndex = 18,
            x = 3,
            y = 42,
            width = 120,
            height = 23,
            words = wordsB,
        )

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }

    private fun writePair(
        bytes: ByteArray,
        offset: Int,
        globalIndex: Int,
        x: Int,
        y: Int,
        width: Int,
        height: Int,
        words: List<Long>,
    ) {
        val recordSize = WIDGET_FIXED_SIZE + words.size * 4
        bytes.putU32(offset + 0x00, WIDGET_PAIR)
        bytes.putU32(offset + 0x04, 0)
        bytes.putU32(offset + 0x08, 0)
        bytes.putU32(offset + 0x0C, (globalIndex shl 16) or recordSize)
        bytes.putU32(offset + 0x10, 0)
        bytes.putU32(offset + 0x14, 0)
        bytes.putU16(offset + 0x18, x and 0xFFFF)
        bytes.putU16(offset + 0x1A, y and 0xFFFF)
        bytes.putU16(offset + 0x1C, width)
        bytes.putU16(offset + 0x1E, height)
        bytes.putU32(offset + 0x20, 0)
        words.forEachIndexed { index, word ->
            bytes.putU32(offset + WIDGET_FIXED_SIZE + index * 4, word)
        }
    }
}
