package dev.fitface.studio.core.format

/** Luminance-preserving tint for RGB565 glyph artwork. */
internal object SpriteTint {
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

    private fun encodeRgb565(red: Int, green: Int, blue: Int): Int {
        val r = (red.coerceIn(0, 255) * 31 + 127) / 255
        val g = (green.coerceIn(0, 255) * 63 + 127) / 255
        val b = (blue.coerceIn(0, 255) * 31 + 127) / 255
        return (r shl 11) or (g shl 5) or b
    }
}
