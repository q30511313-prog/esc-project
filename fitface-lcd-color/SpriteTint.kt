package dev.fitface.studio.core.format

/** Color transforms for RGB565 glyph artwork. */
internal object SpriteTint {
    /**
     * Recolors ordinary RGB565 artwork while preserving its stored luminance.
     * This remains the behavior for RGB565 frames that do not carry a separate
     * coverage/alpha channel.
     */
    fun tintRgb565(
        pixel: Int,
        targetRed: Int,
        targetGreen: Int,
        targetBlue: Int,
        threshold: Int = 16,
    ): Int {
        require(targetRed in 0..255 && targetGreen in 0..255 && targetBlue in 0..255)
        require(threshold in 0..255)

        val red = (((pixel ushr 11) and 0x1F) * 255 + 15) / 31
        val green = (((pixel ushr 5) and 0x3F) * 255 + 31) / 63
        val blue = ((pixel and 0x1F) * 255 + 15) / 31
        val intensity = maxOf(red, green, blue)
        if (intensity <= threshold) return pixel

        val outRed = (targetRed * intensity + 127) / 255
        val outGreen = (targetGreen * intensity + 127) / 255
        val outBlue = (targetBlue * intensity + 127) / 255
        return encodeRgb565(outRed, outGreen, outBlue)
    }

    /**
     * Recolors RGB565+A glyph masks.
     *
     * Samsung stock Fit3 faces can store the glyph RGB565 word as pure black and
     * put the complete glyph shape plus anti-alias coverage in the following alpha
     * byte. In that representation RGB luminance is not a coverage signal, so a
     * luminance-preserving transform would incorrectly leave every visible glyph
     * pixel black. For non-transparent mask pixels, write the requested LCD color
     * directly; the caller keeps the original alpha byte verbatim.
     */
    fun tintRgb565AlphaMask(
        pixel: Int,
        alpha: Int,
        targetRed: Int,
        targetGreen: Int,
        targetBlue: Int,
    ): Int {
        require(alpha in 0..255)
        require(targetRed in 0..255 && targetGreen in 0..255 && targetBlue in 0..255)
        if (alpha == 0) return pixel
        return encodeRgb565(targetRed, targetGreen, targetBlue)
    }

    private fun encodeRgb565(red: Int, green: Int, blue: Int): Int {
        val r = (red.coerceIn(0, 255) * 31 + 127) / 255
        val g = (green.coerceIn(0, 255) * 63 + 127) / 255
        val b = (blue.coerceIn(0, 255) * 31 + 127) / 255
        return (r shl 11) or (g shl 5) or b
    }
}
