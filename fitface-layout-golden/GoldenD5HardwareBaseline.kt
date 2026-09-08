package dev.fitface.studio.core.format

import java.security.MessageDigest

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

    /**
     * Chooses a persisted project only when it belongs to the current D5 baseline family.
     *
     * The D5 validation APK keeps its Android application id across upgrades, so an
     * edited.bin written by the pre-clean-plate build can survive an APK update and would
     * otherwise override [resolve]. That stale container is exactly the hardware symptom
     * observed on style2: the watch keeps rendering the old green stock plate even though
     * the newly-built APK contains the approved cyan D4 plate.
     */
    fun currentOrBaseline(
        faceId: String,
        baseline: Fit3Container,
        persisted: Fit3Container?,
    ): Fit3Container {
        if (persisted == null) return baseline
        if (faceId != TARGET_FACE_ID) return persisted
        return if (hasCurrentD4Plate(persisted)) persisted else baseline
    }

    /** Fingerprint that distinguishes the post-fix D4/style2 family from stale projects. */
    fun hasCurrentD4Plate(container: Fit3Container): Boolean = runCatching {
        val style2 = container.entryByBasename("style2.bin")
        val background = FaceRecordParser.backgroundImage(style2) ?: return@runCatching false
        if (background.width != GoldenD4CleanPlate.WIDTH ||
            background.height != GoldenD4CleanPlate.HEIGHT ||
            background.format != IMAGE_RGB565
        ) {
            return@runCatching false
        }
        val raw = style2.data.copyOfRange(
            background.samplesOffset,
            background.samplesOffset + background.pixelDataSize,
        )
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(raw)
            .joinToString(separator = "") { "%02x".format(it) }
        digest == GoldenD4CleanPlate.RAW_SHA256
    }.getOrDefault(false)
}
