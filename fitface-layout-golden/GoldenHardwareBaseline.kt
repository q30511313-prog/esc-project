package dev.fitface.studio.core.format

/**
 * Hardware-test-only baseline selector.
 *
 * Samsung 00049 is compiled to the full Golden D1 clean-plate + live semantic layout
 * before an editor session is created. Every other face is returned by identity, so
 * this helper cannot become a broad catalogue mutation by accident.
 */
object GoldenHardwareBaseline {
    const val TARGET_FACE_ID = "00049"

    fun resolve(
        faceId: String,
        stock: Fit3Container,
    ): Fit3Container = if (faceId == TARGET_FACE_ID) {
        GoldenD1LayoutCompiler.compile(stock).container
    } else {
        stock
    }
}
