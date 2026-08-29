package dev.fitface.studio.core.format

import java.security.MessageDigest

/**
 * D4 expansion transaction.
 *
 * Replays the approved D3 baseline and then installs the approved style2 layout.
 * D4 is deliberately incremental: style0/style1 must stay byte-identical to the
 * D3 result and stock style3 must remain untouched.
 */
object GoldenD4Compiler {
    private const val WIDTH = 256
    private const val HEIGHT = 402
    private const val STYLE2 = "style2.bin"
    private const val WEATHER_GLOBAL_INDEX = 9
    private const val WEATHER_WIDGET_TYPE = 5
    private const val WEATHER_SEQUENCE_ID = 41

    private data class Target(
        val globalIndex: Int,
        val x: Int,
        val y: Int,
    )

    private val TARGETS = listOf(
        Target(0, 74, 61),
        Target(1, 132, 61),
        Target(2, 160, 61),
        Target(10, 103, 88),
        Target(8, 58, 113),
        Target(3, 77, 128),
        Target(4, 106, 128),
        Target(5, 137, 128),
        Target(6, 169, 128),
        Target(7, 103, 218),
        Target(13, 97, 286),
        Target(11, 163, 283),
        Target(12, 137, 322),
    )

    fun compile(source: Fit3Container): ContainerEdit {
        val d3 = GoldenD3Compiler.compile(source).container
        val locked = listOf("style0.bin", "style1.bin", "style3.bin")
            .associateWith { d3.entryByBasename(it).data.copyOf() }

        val beforeStyle2 = d3.entryByBasename(STYLE2)
        val beforeImages = FaceRecordParser.scanImages(beforeStyle2).size
        val beforeBackground = FaceRecordParser.backgroundImage(beforeStyle2)
            ?: throw Fit3FormatException("$STYLE2: D4 requires a panel background")
        if (beforeBackground.width != WIDTH || beforeBackground.height != HEIGHT) {
            throw Fit3FormatException("$STYLE2: D4 background must be ${WIDTH}x$HEIGHT")
        }

        var current = d3
        var changed = 0

        val plateEdit = FaceEditor.replaceBackgroundInStyle(
            source = current,
            entryBasename = STYLE2,
            width = WIDTH,
            height = HEIGHT,
            argb = GoldenD4CleanPlate.argb(),
        )
        current = plateEdit.container
        changed += plateEdit.changedPayloadBytes

        fun moveUniqueGlobal(target: Target) {
            val records = FaceRecordParser.scanWidgets(current.entryByBasename(STYLE2))
            val record = records.singleOrNull { it.globalIndex == target.globalIndex }
                ?: throw Fit3FormatException(
                    "$STYLE2: D4 widget g${target.globalIndex} missing or ambiguous",
                )
            if (record.x == target.x && record.y == target.y) {
                return
            }
            val edit = FaceEditor.moveWidget(
                source = current,
                entryBasename = STYLE2,
                globalIndex = target.globalIndex,
                widgetType = record.widgetType,
                sequenceId = record.sequenceId,
                x = target.x,
                y = target.y,
            )
            current = edit.container
            changed += edit.changedPayloadBytes
        }

        TARGETS.forEach(::moveUniqueGlobal)

        val weather = FaceRecordParser.scanWidgets(current.entryByBasename(STYLE2))
            .singleOrNull {
                it.globalIndex == WEATHER_GLOBAL_INDEX &&
                    it.widgetType == WEATHER_WIDGET_TYPE &&
                    it.sequenceId == WEATHER_SEQUENCE_ID
            }
            ?: throw Fit3FormatException(
                "$STYLE2: D4 weather g$WEATHER_GLOBAL_INDEX/t$WEATHER_WIDGET_TYPE/seq$WEATHER_SEQUENCE_ID " +
                    "missing or ambiguous",
            )
        if (weather.x != 60 || weather.y != 282) {
            val weatherEdit = FaceEditor.moveWidget(
                source = current,
                entryBasename = STYLE2,
                globalIndex = weather.globalIndex,
                widgetType = weather.widgetType,
                sequenceId = weather.sequenceId,
                x = 60,
                y = 282,
            )
            current = weatherEdit.container
            changed += weatherEdit.changedPayloadBytes
        }

        locked.forEach { (name, bytes) ->
            if (!bytes.contentEquals(current.entryByBasename(name).data)) {
                throw Fit3FormatException("D4 modified locked sibling $name")
            }
        }

        val afterStyle2 = current.entryByBasename(STYLE2)
        if (beforeStyle2.data.contentEquals(afterStyle2.data)) {
            throw Fit3FormatException("D4 would not change $STYLE2")
        }
        if (FaceRecordParser.scanImages(afterStyle2).size != beforeImages) {
            throw Fit3FormatException("D4 changed style2 image record count")
        }
        val afterBackground = FaceRecordParser.backgroundImage(afterStyle2)
            ?: throw Fit3FormatException("$STYLE2: D4 lost its panel background")
        if (afterBackground.width != WIDTH || afterBackground.height != HEIGHT) {
            throw Fit3FormatException("$STYLE2: D4 background geometry drifted")
        }
        if (afterBackground.format != IMAGE_RGB565) {
            throw Fit3FormatException("$STYLE2: D4 clean plate must remain RGB565")
        }
        if (backgroundRgb565Sha256(afterStyle2, afterBackground) != GoldenD4CleanPlate.RAW_SHA256) {
            throw Fit3FormatException("$STYLE2: D4 clean-plate hash did not lock")
        }

        val report = current.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "D4 compile failed validation: " + report.errors.joinToString { it.code },
            )
        }
        if (current.fileSize >= 4 * 1024 * 1024) {
            throw Fit3FormatException("D4 container exceeds the 4 MiB watch limit")
        }
        if (changed <= 0) {
            throw Fit3FormatException("D4 compile would not change any payload bytes")
        }

        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf(STYLE2),
        )
    }

    private fun backgroundRgb565Sha256(entry: ContainerEntry, image: ImageRecord): String {
        val raw = entry.data.copyOfRange(
            image.samplesOffset,
            image.samplesOffset + image.pixelDataSize,
        )
        return MessageDigest.getInstance("SHA-256")
            .digest(raw)
            .joinToString(separator = "") { "%02x".format(it) }
    }
}
