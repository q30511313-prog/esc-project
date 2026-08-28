package dev.fitface.studio.core.format

/** Final four-style hardware baseline: approved D1 style0 plus D5 logical styles1-3. */
object GoldenD5HardwareBaseline {
    const val TARGET_FACE_ID = "00049"

    fun resolve(faceId: String, stock: Fit3Container): Fit3Container {
        if (faceId != TARGET_FACE_ID) return stock

        val combined = GoldenD5Compiler.compile(stock).container
        val style1 = combined.entryByBasename("style1.bin").data.copyOf()
        val style2 = combined.entryByBasename("style2.bin").data.copyOf()
        val style3 = combined.entryByBasename("style3.bin").data.copyOf()

        val optical = GoldenD1OpticalLock.compile(combined).container
        val hardware = GoldenD1HardwareCorrections.compile(optical).container

        if (!style1.contentEquals(hardware.entryByBasename("style1.bin").data) ||
            !style2.contentEquals(hardware.entryByBasename("style2.bin").data) ||
            !style3.contentEquals(hardware.entryByBasename("style3.bin").data)
        ) {
            throw Fit3FormatException("D5 D1 hardware pass modified approved styles1-3")
        }

        val report = hardware.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "D5 hardware baseline failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        if (hardware.fileSize >= 4 * 1024 * 1024) {
            throw Fit3FormatException("D5 hardware baseline exceeds the 4 MiB watch limit")
        }
        return hardware
    }
}
