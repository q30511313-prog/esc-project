package dev.fitface.studio.core.format

/** Dedicated hardware-test baseline for approved Golden D2 (1000028943). */
object GoldenD2HardwareBaseline {
    const val TARGET_FACE_ID = "00049"

    fun resolve(faceId: String, stock: Fit3Container): Fit3Container {
        if (faceId != TARGET_FACE_ID) return stock
        return GoldenD2LayoutCompiler.compile(stock).container
    }
}
