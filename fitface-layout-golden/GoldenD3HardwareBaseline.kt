package dev.fitface.studio.core.format

/** Final combined hardware baseline: approved D1 on style0 plus proven D2 on style1. */
object GoldenD3HardwareBaseline {
    const val TARGET_FACE_ID = "00049"

    fun resolve(faceId: String, stock: Fit3Container): Fit3Container {
        if (faceId != TARGET_FACE_ID) return stock

        val combined = GoldenD3Compiler.compile(stock).container
        val style1 = combined.entryByBasename("style1.bin").data.copyOf()
        val style2 = combined.entryByBasename("style2.bin").data.copyOf()
        val style3 = combined.entryByBasename("style3.bin").data.copyOf()

        val optical = GoldenD1OpticalLock.compile(combined).container
        val hardware = GoldenD1HardwareCorrections.compile(optical).container

        if (!style1.contentEquals(hardware.entryByBasename("style1.bin").data)) {
            throw Fit3FormatException("D3 D1 hardware pass modified approved D2 style1")
        }
        if (!style2.contentEquals(hardware.entryByBasename("style2.bin").data) ||
            !style3.contentEquals(hardware.entryByBasename("style3.bin").data)
        ) {
            throw Fit3FormatException("D3 D1 hardware pass modified untouched sibling styles")
        }
        val report = hardware.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "D3 hardware baseline failed validation: " + report.errors.joinToString { it.code },
            )
        }
        if (hardware.fileSize >= 4 * 1024 * 1024) {
            throw Fit3FormatException("D3 hardware baseline exceeds the 4 MiB watch limit")
        }
        return hardware
    }
}
