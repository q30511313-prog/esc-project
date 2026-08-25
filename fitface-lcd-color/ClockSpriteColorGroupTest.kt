package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ClockSpriteColorGroupTest {
    @Test
    fun selectingHourRecolorsHourMinuteAndSecondPoolsButNotUnrelatedSprite() {
        val source = syntheticClockContainer()
        val beforeEntry = source.entryByBasename("style0.bin")
        val beforeRecords = FaceRecordParser.scanWidgets(beforeEntry)
        val hourUnits = beforeRecords.single { it.sequenceId == 3 }
        val beforeImages = FaceRecordParser.scanImages(beforeEntry)
        val beforeBytes = source.toByteArray()

        val edit = FaceEditor.recolorSpriteWidgetAcrossStyles(
            source = source,
            entryBasenames = listOf("style0.bin"),
            globalIndex = hourUnits.globalIndex,
            sequenceId = hourUnits.sequenceId,
            x = hourUnits.x,
            y = hourUnits.y,
            red = 0xB8,
            green = 0xB8,
            blue = 0xAD,
        )

        val afterEntry = edit.container.entryByBasename("style0.bin")
        val afterImages = FaceRecordParser.scanImages(afterEntry)
        val afterBytes = edit.container.toByteArray()

        // Pool A is shared by hour/minute. Pool B is a physically separate seconds
        // pool, matching Samsung face 00003 style0. Both are one logical clock and
        // must receive the identical raw LCD RGB value from one clock recolor action.
        assertEquals(0xB5B5, afterBytes.u16(afterEntry.offset + afterImages[0].samplesOffset))
        assertEquals(0xB5B5, afterBytes.u16(afterEntry.offset + afterImages[1].samplesOffset))

        // RGB565+A anti-alias/coverage bytes stay byte-identical.
        assertEquals(
            beforeBytes[beforeEntry.offset + beforeImages[0].samplesOffset + 2],
            afterBytes[afterEntry.offset + afterImages[0].samplesOffset + 2],
        )
        assertEquals(
            beforeBytes[beforeEntry.offset + beforeImages[1].samplesOffset + 2],
            afterBytes[afterEntry.offset + afterImages[1].samplesOffset + 2],
        )

        // A non-clock Sprite must not be swept into the clock group.
        assertEquals(0x0000, afterBytes.u16(afterEntry.offset + afterImages[2].samplesOffset))
        assertEquals(
            beforeBytes[beforeEntry.offset + beforeImages[2].samplesOffset + 2],
            afterBytes[afterEntry.offset + afterImages[2].samplesOffset + 2],
        )
        assertEquals(source.fileSize, edit.container.fileSize)
        assertEquals(listOf("style0.bin"), edit.changedStyles)
        assertTrue(edit.container.validate().isValid)
    }

    private fun syntheticClockContainer(): Fit3Container {
        val sequences = listOf(2, 3, 10, 11, 14, 15, 99)
        val xPositions = listOf(0, 37, 90, 127, 180, 218, 20)
        val widgetSize = WIDGET_FIXED_SIZE + 4 // one frame pointer
        val widgetBytes = sequences.size * widgetSize

        val imageDataSize = 3 // 1x1 RGB565+A, no trailer
        val imageRecordSize = IMAGE_HEADER_SIZE + imageDataSize
        val imageCount = 3 // A=hour/min, B=seconds, C=unrelated
        val imageBytes = imageCount * imageRecordSize
        val styleSize = STYLE_HEADER_SIZE + widgetBytes + imageBytes
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
        bytes.putU32(style + 0x04, sequences.size)
        bytes.putU32(style + 0x08, widgetBytes)
        bytes.putU32(style + 0x0C, imageBytes)
        bytes.putU32(style + 0x10, 0)
        bytes.putU32(style + 0x14, STYLE_HEADER_SIZE + widgetBytes)

        sequences.forEachIndexed { index, sequenceId ->
            val widget = style + STYLE_HEADER_SIZE + index * widgetSize
            bytes.putU32(widget + 0x00, WIDGET_SPRITE)
            bytes.putU32(widget + 0x04, sequenceId)
            bytes.putU32(widget + 0x08, 0)
            bytes.putU32(widget + 0x0C, ((index + 1) shl 16) or widgetSize)
            bytes.putU32(widget + 0x10, 0)
            bytes.putU32(widget + 0x14, 0)
            bytes.putU16(widget + 0x18, xPositions[index])
            bytes.putU16(widget + 0x1A, if (sequenceId == 99) 250 else 166)
            bytes.putU16(widget + 0x1C, 38)
            bytes.putU16(widget + 0x1E, 68)
            bytes.putU32(widget + 0x20, 1) // one frame

            val imageIndex = when (sequenceId) {
                14, 15 -> 1 // separate seconds pool
                99 -> 2 // unrelated Sprite pool
                else -> 0 // shared hour/minute pool
            }
            bytes.putU32(widget + WIDGET_FIXED_SIZE, imageIndex * imageRecordSize)
        }

        val imageSection = style + STYLE_HEADER_SIZE + widgetBytes
        val alphas = intArrayOf(0x80, 0x40, 0xFF)
        repeat(imageCount) { index ->
            val image = imageSection + index * imageRecordSize
            bytes.putU16(image + 0x00, 1)
            bytes.putU16(image + 0x02, 1)
            bytes.putU16(image + 0x04, IMAGE_RGB565_ALPHA)
            bytes.putU16(image + 0x06, 0)
            bytes.putU32(image + 0x08, imageDataSize)
            bytes.putU16(image + IMAGE_HEADER_SIZE, 0x0000)
            bytes[image + IMAGE_HEADER_SIZE + 2] = alphas[index].toByte()
        }

        bytes.putU16(directory + 0x48, Crc16.ccittFalse(bytes, bodyOffset, bytes.size))
        bytes.putU16(0x10, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }
}
