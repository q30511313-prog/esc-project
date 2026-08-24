package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.LcdPalette
import org.junit.Assert.assertEquals
import org.junit.Test

class LcdPaletteTest {
    @Test
    fun approvedSilverMatchesFinalCasioReference9f9e99() {
        assertEquals(0xFF9F9E99.toInt(), LcdPalette.SILVER_ARGB)
        assertEquals(0x9F, LcdPalette.SILVER_RED)
        assertEquals(0x9E, LcdPalette.SILVER_GREEN)
        assertEquals(0x99, LcdPalette.SILVER_BLUE)
    }
}
