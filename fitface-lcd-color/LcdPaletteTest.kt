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
    fun fit3OpticalSilverCompensatesLavenderPanelShift() {
        // Two independent real-Fit3 captures show requested neutral #B8B8AD
        // rendering with Green suppressed and Blue elevated. The inverse payload
        // keeps Red fixed, raises Green, and lowers Blue. #B8C794 also quantizes
        // cleanly to RGB565 0xB631 for the clock/colon/separator raster path.
        assertEquals(0xB8, LcdPalette.FIT3_OPTICAL_RED)
        assertEquals(0xC7, LcdPalette.FIT3_OPTICAL_GREEN)
        assertEquals(0x94, LcdPalette.FIT3_OPTICAL_BLUE)
        assertEquals(0xFFB8C794.toInt(), LcdPalette.FIT3_OPTICAL_ARGB)
    }
}
