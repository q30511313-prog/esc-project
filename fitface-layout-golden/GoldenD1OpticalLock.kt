package dev.fitface.studio.core.format

/**
 * Final Golden D1 optical-colour pass.
 *
 * This stage is intentionally last: it accepts an already-compiled Samsung 00049
 * style0 Golden layout, recolours only the live foreground renderer paths to the
 * real-device approved optical payload, and proves that the clean plate plus sibling
 * styles remain byte-identical. No record or image inventory is created here.
 */
object GoldenD1OpticalLock {
    const val LOGICAL_RGB888 = 0xB8B8AD
    const val OPTICAL_RGB888 = 0xB5B6BD
    const val OPTICAL_RGB565 = 0xB5B7

    private const val OPTICAL_ARGB: Int = 0xFFB5B6BD.toInt()
    private const val OPTICAL_RED = 0xB5
    private const val OPTICAL_GREEN = 0xB6
    private const val OPTICAL_BLUE = 0xBD
    private const val MAX_FACE_BYTES = 4 * 1024 * 1024

    fun compile(source: Fit3Container): ContainerEdit {
        val styleName = "style0.bin"
        val beforeStyle0 = source.entryByBasename(styleName)
        val beforeRecords = FaceRecordParser.scanWidgets(beforeStyle0)
        val beforeImageCount = FaceRecordParser.scanImages(beforeStyle0).size
        val beforeBackground = backgroundSamples(beforeStyle0)
        val siblingNames = listOf("style1.bin", "style2.bin", "style3.bin")
        val siblingBytes = siblingNames.associateWith {
            source.entryByBasename(it).data.copyOf()
        }

        // Fail closed against the exact post-layout identities. This prevents the
        // optical pass from becoming a generic face-wide recolour operation.
        requireRecord(beforeRecords, 1, WIDGET_COMP, 0, 65, 47)
        requireRecord(beforeRecords, 2, WIDGET_PAIR, 17, 107, 80)
        requireRecord(beforeRecords, 3, WIDGET_SPRITE, 2, 77, 139)
        requireRecord(beforeRecords, 4, WIDGET_SPRITE, 3, 106, 139)
        requireRecord(beforeRecords, 5, WIDGET_SPRITE, 10, 142, 139)
        requireRecord(beforeRecords, 6, WIDGET_SPRITE, 11, 171, 139)
        requireRecord(beforeRecords, 7, WIDGET_SPRITE, 69, 113, 261)
        requireRecord(beforeRecords, 8, WIDGET_COMP, 0, 171, 260)
        requireRecord(beforeRecords, 9, WIDGET_PAIR, 5, 48, 120)
        requireRecord(beforeRecords, 11, WIDGET_COMP, 0, 82, 336)
        requireRecord(beforeRecords, 15, WIDGET_PAIR, 14, 48, 257)
        requireRecord(beforeRecords, 16, WIDGET_PAIR, 15, 72, 257)
        requireRecord(beforeRecords, 17, WIDGET_PAIR, 69, 112, 301)

        var current = source
        var changed = 0

        fun accept(edit: ContainerEdit) {
            current = edit.container
            changed += edit.changedPayloadBytes
        }

        // Main HH:MM shares one native Sprite digit pool, so one anchored recolour
        // updates that pool without touching the clean plate or weather pool.
        accept(
            FaceEditor.recolorSpriteWidgetAcrossStyles(
                source = current,
                entryBasenames = listOf(styleName),
                globalIndex = 4,
                sequenceId = 3,
                x = 106,
                y = 139,
                red = OPTICAL_RED,
                green = OPTICAL_GREEN,
                blue = OPTICAL_BLUE,
            ),
        )

        // Weather keeps its existing 24-frame inventory; recolour only that pool.
        accept(
            FaceEditor.recolorSpriteWidgetAcrossStyles(
                source = current,
                entryBasenames = listOf(styleName),
                globalIndex = 7,
                sequenceId = 69,
                x = 113,
                y = 261,
                red = OPTICAL_RED,
                green = OPTICAL_GREEN,
                blue = OPTICAL_BLUE,
            ),
        )

        listOf(
            intArrayOf(2, 17, 107, 80),
            intArrayOf(9, 5, 48, 120),
            intArrayOf(15, 14, 48, 257),
            intArrayOf(16, 15, 72, 257),
            intArrayOf(17, 69, 112, 301),
        ).forEach { identity ->
            accept(
                FaceEditor.recolorPairWidgetAcrossStyles(
                    source = current,
                    entryBasenames = listOf(styleName),
                    globalIndex = identity[0],
                    sequenceId = identity[1],
                    x = identity[2],
                    y = identity[3],
                    colorArgb = OPTICAL_ARGB,
                ),
            )
        }

        listOf(
            intArrayOf(1, 0, 65, 47),
            intArrayOf(8, 0, 171, 260),
            intArrayOf(11, 0, 82, 336),
        ).forEach { identity ->
            accept(
                FaceEditor.recolorCompositeWidgetAcrossStyles(
                    source = current,
                    entryBasenames = listOf(styleName),
                    globalIndex = identity[0],
                    sequenceId = identity[1],
                    x = identity[2],
                    y = identity[3],
                    colorArgb = OPTICAL_ARGB,
                ),
            )
        }

        val afterStyle0 = current.entryByBasename(styleName)
        if (FaceRecordParser.scanImages(afterStyle0).size != beforeImageCount) {
            throw Fit3FormatException("Golden D1 optical lock changed style0 image record count")
        }
        if (!beforeBackground.contentEquals(backgroundSamples(afterStyle0))) {
            throw Fit3FormatException("Golden D1 optical lock modified the clean-plate background")
        }
        siblingBytes.forEach { (name, bytes) ->
            if (!bytes.contentEquals(current.entryByBasename(name).data)) {
                throw Fit3FormatException("Golden D1 optical lock modified sibling $name")
            }
        }
        if (current.fileSize >= MAX_FACE_BYTES) {
            throw Fit3FormatException(
                "Golden D1 optical-locked container exceeds 4 MiB: ${current.fileSize}",
            )
        }
        val report = current.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden D1 optical lock failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        if (changed <= 0) {
            throw Fit3FormatException("Golden D1 optical lock would not change any bytes")
        }

        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf(styleName),
        )
    }

    private fun requireRecord(
        records: List<WidgetRecord>,
        globalIndex: Int,
        type: Int,
        sequence: Int,
        x: Int,
        y: Int,
    ): WidgetRecord = records.singleOrNull {
        it.globalIndex == globalIndex &&
            it.widgetType == type &&
            it.sequenceId == sequence &&
            it.x == x &&
            it.y == y
    } ?: throw Fit3FormatException(
        "Golden D1 optical identity g$globalIndex/type$type/seq$sequence@($x,$y) is missing or ambiguous",
    )

    private fun backgroundSamples(entry: Fit3Entry): ByteArray {
        val image = FaceRecordParser.backgroundImage(entry)
            ?: throw Fit3FormatException("style0.bin: Golden D1 optical lock requires a background")
        val byteCount = image.width * image.height * image.bytesPerPixel
        return entry.data.copyOfRange(image.samplesOffset, image.samplesOffset + byteCount)
    }
}
