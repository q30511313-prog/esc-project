package dev.fitface.studio.core.format

/**
 * Hardware-test-only baseline selector.
 *
 * Samsung 00049 is compiled to the full Golden D1 clean-plate + live semantic layout,
 * receives the approved optical-colour lock, and finally receives only the renderer
 * corrections proven from real Galaxy Fit3 photos. Every other face is returned by
 * identity, so this helper cannot become a broad catalogue mutation by accident.
 */
object GoldenHardwareBaseline {
    const val TARGET_FACE_ID = "00049"

    fun resolve(
        faceId: String,
        stock: Fit3Container,
    ): Fit3Container = if (faceId == TARGET_FACE_ID) {
        val layout = GoldenD1LayoutCompiler.compile(stock).container
        val optical = GoldenD1OpticalLock.compile(layout).container
        GoldenD1HardwareCorrections.compile(optical).container
    } else {
        stock
    }
}
