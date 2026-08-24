package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.LcdPalette
import org.junit.Assert.assertEquals
import org.junit.Test

class LcdPaletteTest {
    @Test
    fun approvedSilverIsCoolNeutralAeb4b2() {
        assertEquals(0xFFAEB4B2.toInt(), LcdPalette.SILVER_ARGB)
        assertEquals(0xAE, LcdPalette.SILVER_RED)
        assertEquals(0xB4, LcdPalette.SILVER_GREEN)
        assertEquals(0xB2, LcdPalette.SILVER_BLUE)
    }
}
