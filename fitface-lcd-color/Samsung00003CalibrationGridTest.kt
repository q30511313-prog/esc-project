package dev.fitface.studio.core.format

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00003CalibrationGridTest {
    @Test
    fun style3OpticalCalibrationAddsSingleShotRgb565Matrix() {
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
        val background = FaceRecordParser.backgroundImage(afterEntry)
            ?: error("style3 background image missing")
        val bytes = edit.container.toByteArray()

        // One transfer must expose 16 distinct, already-quantized RGB565 samples.
        // R5 stays at 22 while G6 steps 47 -> 44 and B5 steps 20 -> 23.
        // Patch 1 is the current v10 payload (0xB5F4); patch 7 is the logical
        // #B8B8AD quantization (0xB5B5); patch 11 is near digital neutral.
        val expected = intArrayOf(
            0xB5F4, 0xB5D4, 0xB5B4, 0xB594,
            0xB5F5, 0xB5D5, 0xB5B5, 0xB595,
            0xB5F6, 0xB5D6, 0xB5B6, 0xB596,
            0xB5F7, 0xB5D7, 0xB5B7, 0xB597,
        )
        val xs = intArrayOf(24, 76, 128, 180)
        val ys = intArrayOf(10, 110, 290, 340)
        val patchSize = 40

        expected.forEachIndexed { index, color ->
            val x = xs[index % 4] + patchSize / 2
            val y = ys[index / 4] + patchSize / 2
            val absolute = afterEntry.offset +
                background.samplesOffset +
                (y * background.width + x) * background.bytesPerPixel
            assertEquals("patch ${index + 1}", color, bytes.u16(absolute))
        }

        assertEquals(source.fileSize, edit.container.fileSize)
        assertTrue(edit.container.validate().isValid)
    }
}
