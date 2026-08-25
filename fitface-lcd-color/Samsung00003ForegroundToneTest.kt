package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00003ForegroundToneTest {
    @Test
    fun clockLcdActionAlsoUnifiesValueAndCompositeForegroundColors() {
        val source = syntheticSamsung00003Style3()
        val beforeEntry = source.entryByBasename("style3.bin")
        val beforeRecords = FaceRecordParser.scanWidgets(beforeEntry)
        val selected = beforeRecords.single {
            it.widgetType == WIDGET_SPRITE && it.sequenceId == 3
        }
        val beforePair = beforeRecords.single { it.widgetType == WIDGET_PAIR }
        val beforeComposite = beforeRecords.single { it.widgetType == WIDGET_COMP }

        assertEquals(0xFFD6E1F9L, beforePair.words[0])
        assertEquals(0xFFD6E1F9L, beforeComposite.words[13])
        assertEquals(0x11223344L, beforeComposite.words[12])

        val edit = FaceEditor.recolorSpriteWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style3.bin"),
            globalIndex = selected.globalIndex,
            sequenceId = selected.sequenceId,
            x = selected.x,
            y = selected.y,
            red = 0xB8,
            green = 0xB8,
            blue = 0xAD,
        )

        val afterRecords = FaceRecordParser.scanWidgets(
            edit.container.entryByBasename("style3.bin"),
        )
        val afterPair = afterRecords.single { it.widgetType == WIDGET_PAIR }
        val afterComposite = afterRecords.single { it.widgetType == WIDGET_COMP }

        // One G-SHOCK clock action must put the non-clock foreground records on
        // exactly the same opaque LCD gray as the time, rather than leaving the
        // stock style3 blue/lilac #D6E1F9 behind.
        assertEquals(0xFFB8B8ADL, afterPair.words[0])
        assertEquals(0xFFB8B8ADL, afterComposite.words[13])

        // Only the proven color words may change.
        assertEquals(0x11223344L, afterComposite.words[12])
        assertTrue(edit.container.validate().isValid)
    }

    private fun syntheticSamsung00003Style3(): Fit3Container {
        val spriteSequences = listOf(2, 3, 10, 11, 14, 15)
        val spriteX = listOf(0, 37, 90, 127, 180, 218)
        val staticRecordSize = 40
        val spriteRecordSize = WIDGET_FIXED_SIZE + 4
        val pairWords = listOf(0xFFD6E1F9L, 0x01000001L, 0x0001FFFFL, 0L, 0L)
        val pairRecordSize = WIDGET_FIXED_SIZE + pairWords.size * 4
        val compositeWords = MutableList(16) { 0L }.also {
            it[12] = 0x11223344L
            it[13] = 0xFFD6E1F9L
        }
        val compositeRecordSize = WIDGET_FIXED_SIZE + compositeWords.size * 4

        val widgetCount = 1 + spriteSequences.size + 2 + 1 + 1
        val widgetBytes = staticRecordSize +
            spriteSequences.size * spriteRecordSize +
            2 * staticRecordSize + pairRecordSize + compositeRecordSize

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
            bytes.putU16(cursor + 0x18, x and 0xFFFF)
            bytes.putU16(cursor + 0x1A, y and 0xFFFF)
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

        bytes.putU32(cursor + 0x00, WIDGET_PAIR)
        bytes.putU32(cursor + 0x04, 37)
        bytes.putU32(cursor + 0x08, 0)
        bytes.putU32(cursor + 0x0C, (9 shl 16) or pairRecordSize)
        bytes.putU32(cursor + 0x10, 0)
        bytes.putU32(cursor + 0x14, 0)
        bytes.putU16(cursor + 0x18, (-174) and 0xFFFF)
        bytes.putU16(cursor + 0x1A, 68)
        bytes.putU16(cursor + 0x1C, 65)
        bytes.putU16(cursor + 0x1E, 42)
        bytes.putU32(cursor + 0x20, 3)
        pairWords.forEachIndexed { index, word ->
            bytes.putU32(cursor + WIDGET_FIXED_SIZE + index * 4, word)
        }
        cursor += pairRecordSize

        bytes.putU32(cursor + 0x00, WIDGET_COMP)
        bytes.putU32(cursor + 0x04, 0)
        bytes.putU32(cursor + 0x08, 0)
        bytes.putU32(cursor + 0x0C, (10 shl 16) or compositeRecordSize)
        bytes.putU32(cursor + 0x10, 0)
        bytes.putU32(cursor + 0x14, 0)
        bytes.putU16(cursor + 0x18, 134)
        bytes.putU16(cursor + 0x1A, 68)
        bytes.putU16(cursor + 0x1C, 120)
        bytes.putU16(cursor + 0x1E, 42)
        bytes.putU32(cursor + 0x20, 0)
        compositeWords.forEachIndexed { index, word ->
            bytes.putU32(cursor + WIDGET_FIXED_SIZE + index * 4, word)
        }
        cursor += compositeRecordSize

        val imageSection = style + STYLE_HEADER_SIZE + widgetBytes
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
        val separatorRects = listOf(
            intArrayOf(14, 120, 133, 134),
            intArrayOf(139, 245, 133, 134),
            intArrayOf(14, 241, 264, 265),
        )
        separatorRects.forEach { rect ->
            for (y in rect[2]..rect[3]) {
                for (x in rect[0]..rect[1]) {
                    val pixel = y * 256 + x
                    bytes.putU16(bg + pixel * 3, 0x4A49)
                }
            }
        }

        val digit = imageSection + backgroundRecordSize
        bytes.putU16(digit + 0x00, 1)
        bytes.putU16(digit + 0x02, 1)
        bytes.putU16(digit + 0x04, IMAGE_RGB565)
        bytes.putU16(digit + 0x06, 0)
        bytes.putU32(digit + 0x08, 2)
        bytes.putU16(digit + IMAGE_HEADER_SIZE, 0xFFFF)

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
