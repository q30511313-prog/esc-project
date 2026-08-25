package dev.fitface.studio.core.format

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LcdSpriteTintTest {
    @Test
    fun blackPixelStaysBlack() {
        assertEquals(0x0000, SpriteTint.tintRgb565(0x0000, 0xC9, 0xCE, 0xCB))
    }

    @Test
    fun brightMagentaBecomesNeutralLcdSilver() {
        val tinted = SpriteTint.tintRgb565(0xF81F, 0xC9, 0xCE, 0xCB)
        assertNotEquals(0xF81F, tinted)
        val r = ((tinted ushr 11) and 0x1F) * 255 / 31
        val g = ((tinted ushr 5) and 0x3F) * 255 / 63
        val b = (tinted and 0x1F) * 255 / 31
        assertTrue(kotlin.math.abs(r - g) <= 12)
        assertTrue(kotlin.math.abs(g - b) <= 12)
        assertTrue(r in 180..220)
    }

    @Test
    fun antialiasedEdgeKeepsRelativeBrightness() {
        val bright = SpriteTint.tintRgb565(0xFFFF, 0xC9, 0xCE, 0xCB)
        val dim = SpriteTint.tintRgb565(0x8410, 0xC9, 0xCE, 0xCB)
        val brightR = ((bright ushr 11) and 0x1F) * 255 / 31
        val dimR = ((dim ushr 11) and 0x1F) * 255 / 31
        assertTrue(brightR > dimR)
        assertTrue(dimR > 40)
    }

    @Test
    fun opaqueBlackAlphaMaskPixelReceivesTargetRgb() {
        assertEquals(
            0xB5B5,
            SpriteTint.tintRgb565AlphaMask(
                pixel = 0x0000,
                alpha = 0xFF,
                targetRed = 0xB8,
                targetGreen = 0xB8,
                targetBlue = 0xAD,
            ),
        )
    }

    @Test
    fun transparentAlphaMaskPixelKeepsStoredRgb() {
        assertEquals(
            0x0000,
            SpriteTint.tintRgb565AlphaMask(
                pixel = 0x0000,
                alpha = 0x00,
                targetRed = 0xB8,
                targetGreen = 0xB8,
                targetBlue = 0xAD,
            ),
        )
    }
}
