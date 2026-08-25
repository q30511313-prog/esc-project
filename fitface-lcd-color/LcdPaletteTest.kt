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
}
