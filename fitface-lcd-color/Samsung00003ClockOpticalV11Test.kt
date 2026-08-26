package dev.fitface.studio.core.format

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00003ClockOpticalV11Test {
    @Test
    fun style3ForegroundUsesPatch15HardwareCalibration() {
        val fixture = Samsung00003ClockOpticalCompensationTest::class.java
            .getDeclaredMethod("syntheticSamsung00003Style3")
            .also { it.isAccessible = true }
        val source = fixture.invoke(Samsung00003ClockOpticalCompensationTest()) as Fit3Container
        val beforeEntry = source.entryByBasename("style3.bin")
        val selected = FaceRecordParser.scanWidgets(beforeEntry).single {
            it.widgetType == WIDGET_SPRITE && it.sequenceId == 3
        }

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

        val afterEntry = edit.container.entryByBasename("style3.bin")
        val afterImages = FaceRecordParser.scanImages(afterEntry)
        val afterRecords = FaceRecordParser.scanWidgets(afterEntry)
        val bytes = edit.container.toByteArray()

        val digit = afterEntry.offset + afterImages[1].samplesOffset
        val colon = afterEntry.offset + afterImages[2].samplesOffset

        // Physical Fit3 calibration patch 15 was selected by eye.
        // Representative RGB888 #B5B6BD must quantize to RGB565 0xB5B7.
        assertEquals(0xB5B7, bytes.u16(digit))
        assertEquals(0xB5B7, bytes.u16(colon))

        // VALUE/COMPOSITE use the same v11 payload so every renderer path
        // converges on the selected physical-screen tone.
        val pair = afterRecords.single { it.widgetType == WIDGET_PAIR }
        val composite = afterRecords.single { it.widgetType == WIDGET_COMP }
        assertEquals(0xFFB5B6BDL, pair.words[0])
        assertEquals(0xFFB5B6BDL, composite.words[13])

        val background = afterEntry.offset + afterImages[0].samplesOffset
        val lineOffset = (133 * 256 + 14) * 3
        assertEquals(
            SpriteTint.tintRgb565(0x4A49, 0xB5, 0xB6, 0xBD),
            bytes.u16(background + lineOffset),
        )

        assertEquals(source.fileSize, edit.container.fileSize)
        assertTrue(edit.container.validate().isValid)
    }
}
