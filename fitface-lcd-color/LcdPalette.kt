package dev.fitface.studio.core.model

/** Bright warm-neutral LCD gray sampled from the supplied G-SHOCK reference display. */
object LcdPalette {
    val SILVER_ARGB: Int = 0xFFB8B8AD.toInt()
    const val SILVER_RED: Int = 0xB8
    const val SILVER_GREEN: Int = 0xB8
    const val SILVER_BLUE: Int = 0xAD

    /**
     * Fit3 OLED payload calibration for the logical #B8B8AD Casio/MIP tone.
     * Real-device captures show the panel/render path suppressing Green and
     * elevating Blue; this inverse payload is intentionally device/face scoped
     * by FaceEditor and must not replace the user-facing logical palette.
     */
    val FIT3_OPTICAL_ARGB: Int = 0xFFB8C794.toInt()
    const val FIT3_OPTICAL_RED: Int = 0xB8
    const val FIT3_OPTICAL_GREEN: Int = 0xC7
    const val FIT3_OPTICAL_BLUE: Int = 0x94
}
