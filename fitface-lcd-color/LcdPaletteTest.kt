package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.LcdPalette
import org.junit.Assert.assertEquals
import org.junit.Test

class LcdPaletteTest {
    @Test
    fun approvedSilverMatchesBrightCasioReferenceB8B8AD() {
        assertEquals(0xFFB8B8AD.toInt(), LcdPalette.SILVER_ARGB)
        assertEquals(0xB8, LcdPalette.SILVER_RED)
        assertEquals(0xB8, LcdPalette.SILVER_GREEN)
        assertEquals(0xAD, LcdPalette.SILVER_BLUE)
    }

    @Test
    fun fit3OpticalSilverUsesPerceptualMidpointAfterGreenOvershoot() {
        // v9 (#B8C794) looked neutral to the phone camera but visibly green to the
        // human eye. Keep the correction direction, but back off Green and restore
        // Blue toward the logical #B8B8AD target. The first perceptual midpoint
        // candidate is #B8C0A1; RGB565 rounds it to 0xB5F4.
        assertEquals(0xB8, LcdPalette.FIT3_OPTICAL_RED)
        assertEquals(0xC0, LcdPalette.FIT3_OPTICAL_GREEN)
        assertEquals(0xA1, LcdPalette.FIT3_OPTICAL_BLUE)
        assertEquals(0xFFB8C0A1.toInt(), LcdPalette.FIT3_OPTICAL_ARGB)
    }
}
