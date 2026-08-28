package dev.fitface.studio.core.format

/**
 * D5 expansion transaction for approved design04_8942 / 1000028942.
 *
 * D4 already owns style0/style1/style2. D5 mutates only style3, reusing the same
 * proven Samsung 00049 live resources and the Korean locale expansion installed by D1.
 * All semantic lookups are fail-closed against the pristine style3 identities.
 */
object GoldenD5Compiler {
    private const val WIDTH = 256
    private const val HEIGHT = 402
    private const val STYLE3 = "style3.bin"

    fun compile(source: Fit3Container): ContainerEdit {
        val d4 = GoldenD4Compiler.compile(source).container
        val lockedSiblings = listOf("style0.bin", "style1.bin", "style2.bin")
            .associateWith { d4.entryByBasename(it).data.copyOf() }
        val beforeStyle3 = d4.entryByBasename(STYLE3)
        val beforeStyle3Bytes = beforeStyle3.data.copyOf()
        val beforeImages = FaceRecordParser.scanImages(beforeStyle3).size
        val beforeBackground = FaceRecordParser.backgroundImage(beforeStyle3)
            ?: throw Fit3FormatException("$STYLE3: D5 requires a panel background")
        if (beforeBackground.width != WIDTH || beforeBackground.height != HEIGHT) {
            throw Fit3FormatException("$STYLE3: D5 background must be ${WIDTH}x$HEIGHT")
        }

        var current = d4
        var changed = 0

        fun accept(edit: ContainerEdit) {
            current = edit.container
            changed += edit.changedPayloadBytes
        }

        // Independent live seconds in the compact right-hand design04 box.
        accept(remapPairAndMove(current, 15, 29, 23, 360, 14, 181, 180))
        accept(remapPairAndMove(current, 16, 48, 101, 360, 15, 193, 180))

        // Korean AM/PM uses the locale table already installed by approved D1.
        accept(remapPairAndMove(current, 9, 41, 172, 217, 5, 47, 127))

        // design04 top strip: compact month/day, weekday, battery gauge and value.
        accept(moveExact(current, 1, WIDGET_COMP, 0, 119, 40, 55, 90))
        accept(moveExact(current, 2, WIDGET_PAIR, 17, 179, 36, 105, 76))
        accept(moveExact(current, 10, WIDGET_BADGE, 37, 34, 301, 173, 66))
        accept(moveExact(current, 11, WIDGET_COMP, 0, 140, 292, 175, 88))

        // HH:MM child origins derived from the approved D4 optical arrangement,
        // mapped from design03 TIME width 115 to design04 TIME width 107.
        accept(moveExact(current, 3, WIDGET_SPRITE, 2, 32, 93, 55, 147))
        accept(moveExact(current, 4, WIDGET_SPRITE, 3, 86, 93, 82, 147))
        accept(moveExact(current, 5, WIDGET_SPRITE, 10, 32, 174, 111, 147))
        accept(moveExact(current, 6, WIDGET_SPRITE, 11, 88, 174, 141, 147))

        // design04 lower weather strip.
        accept(moveExact(current, 7, WIDGET_SPRITE, 69, 180, 102, 59, 262))
        accept(wireWeatherTextToExistingLocale(current, 99, 272))
        accept(moveExact(current, 8, WIDGET_COMP, 0, 170, 134, 169, 272))

        lockedSiblings.forEach { (name, bytes) ->
            if (!bytes.contentEquals(current.entryByBasename(name).data)) {
                throw Fit3FormatException("D5 modified D4-approved sibling $name")
            }
        }

        val afterStyle3 = current.entryByBasename(STYLE3)
        if (beforeStyle3Bytes.contentEquals(afterStyle3.data)) {
            throw Fit3FormatException("D5 did not change style3")
        }
        if (FaceRecordParser.scanImages(afterStyle3).size != beforeImages) {
            throw Fit3FormatException("D5 changed style3 image record count")
        }
        val afterBackground = FaceRecordParser.backgroundImage(afterStyle3)
            ?: throw Fit3FormatException("$STYLE3: D5 lost its panel background")
        if (afterBackground.width != WIDTH || afterBackground.height != HEIGHT) {
            throw Fit3FormatException("$STYLE3: D5 background geometry drifted")
        }

        val report = current.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "D5 compile failed validation: " + report.errors.joinToString { it.code },
            )
        }
        if (current.fileSize >= 4 * 1024 * 1024) {
            throw Fit3FormatException("D5 container exceeds the 4 MiB watch limit")
        }
        if (changed <= 0) {
            throw Fit3FormatException("D5 compile would not change any bytes")
        }

        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf(STYLE3),
        )
    }

    private fun remapPairAndMove(
        source: Fit3Container,
        globalIndex: Int,
        oldSequence: Int,
        oldX: Int,
        oldY: Int,
        newSequence: Int,
        newX: Int,
        newY: Int,
    ): ContainerEdit {
        val record = FaceRecordParser.scanWidgets(source.entryByBasename(STYLE3)).singleOrNull {
            it.globalIndex == globalIndex &&
                it.widgetType == WIDGET_PAIR &&
                it.sequenceId == oldSequence &&
                it.x == oldX &&
                it.y == oldY
        } ?: throw Fit3FormatException(
            "$STYLE3: D5 Pair g$globalIndex/seq$oldSequence@($oldX,$oldY) missing or ambiguous",
        )
        val expectedBinding = if (globalIndex == 9) 1 else 2
        if ((record.words.getOrNull(1)?.toInt()?.and(0xFF)) != expectedBinding) {
            throw Fit3FormatException("$STYLE3: D5 Pair g$globalIndex binding drifted")
        }

        val remapped = FaceEditor.remapPairSequence(
            source = source,
            entryBasename = STYLE3,
            globalIndex = globalIndex,
            originalSequenceId = oldSequence,
            x = oldX,
            y = oldY,
            newSequenceId = newSequence,
        )
        val moved = FaceEditor.moveWidget(
            source = remapped.container,
            entryBasename = STYLE3,
            globalIndex = globalIndex,
            widgetType = WIDGET_PAIR,
            sequenceId = newSequence,
            x = newX,
            y = newY,
        )
        return ContainerEdit(
            container = moved.container,
            changedPayloadBytes = remapped.changedPayloadBytes + moved.changedPayloadBytes,
            changedStyles = listOf(STYLE3),
        )
    }

    private fun moveExact(
        source: Fit3Container,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        oldX: Int,
        oldY: Int,
        newX: Int,
        newY: Int,
    ): ContainerEdit {
        FaceRecordParser.scanWidgets(source.entryByBasename(STYLE3)).singleOrNull {
            it.globalIndex == globalIndex &&
                it.widgetType == widgetType &&
                it.sequenceId == sequenceId &&
                it.x == oldX &&
                it.y == oldY
        } ?: throw Fit3FormatException(
            "$STYLE3: D5 widget g$globalIndex/type$widgetType/seq$sequenceId@($oldX,$oldY) missing or ambiguous",
        )
        return FaceEditor.moveWidget(
            source = source,
            entryBasename = STYLE3,
            globalIndex = globalIndex,
            widgetType = widgetType,
            sequenceId = sequenceId,
            x = newX,
            y = newY,
        )
    }

    private fun wireWeatherTextToExistingLocale(
        source: Fit3Container,
        x: Int,
        y: Int,
    ): ContainerEdit {
        val locale = source.entryByBasename("font_ko.bin")
        if (locale.data.size < 0x18 || locale.data.u32(8) != 38L) {
            throw Fit3FormatException(
                "D5 requires the already-installed 14 AM/PM + 24 weather locale groups",
            )
        }

        val entry = source.entryByBasename(STYLE3)
        val donor = FaceRecordParser.scanWidgets(entry).singleOrNull {
            it.globalIndex == 17 &&
                it.widgetType == WIDGET_PAIR &&
                it.sequenceId == 115 &&
                it.x == 179 &&
                it.y == 360
        } ?: throw Fit3FormatException(
            "$STYLE3: D5 weather-text donor g17/seq115@(179,360) missing or ambiguous",
        )
        if ((donor.words.getOrNull(1)?.toInt()?.and(0xFF)) != 2 ||
            donor.words.getOrNull(2) != 0x0002FFFFL
        ) {
            throw Fit3FormatException("$STYLE3: D5 weather-text donor wiring drifted")
        }

        val output = source.toByteArray()
        val before = output.copyOf()
        val base = entry.offset + donor.recordOffset
        output.putU32(base + 0x04, 69)
        output.putU16(base + 0x18, x and 0xFFFF)
        output.putU16(base + 0x1A, y and 0xFFFF)
        output.putU32(base + WIDGET_FIXED_SIZE + 2 * 4, 0x0002000E)

        val changed = (entry.offset until entry.end).count { before[it] != output[it] }
        if (changed == 0) {
            throw Fit3FormatException("D5 weather-text wiring would not change any bytes")
        }

        val directoryOffset = CONTAINER_HEADER_SIZE + entry.index * DIRECTORY_ENTRY_SIZE
        output.putU16(
            directoryOffset + DIRECTORY_PATH_SIZE + 8,
            Crc16.ccittFalse(output, entry.offset, entry.end),
        )
        output.putU16(
            0x10,
            Crc16.ccittFalse(output, CONTAINER_HEADER_SIZE, output.size),
        )
        val parsed = Fit3Container.parse(output)
        val report = parsed.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "D5 weather-text wiring failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        return ContainerEdit(
            container = parsed,
            changedPayloadBytes = changed,
            changedStyles = listOf(STYLE3),
        )
    }
}
