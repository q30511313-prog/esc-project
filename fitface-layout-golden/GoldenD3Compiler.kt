package dev.fitface.studio.core.format

/**
 * D3 expansion transaction.
 *
 * Produces the first two approved slots in one container:
 * - style0 = approved D1 (1000028944)
 * - style1 = approved D2 (1000028943)
 *
 * D1 is compiled first because it owns the one-time Korean AM/PM + weather locale
 * expansion. style1 then points its existing Pair donors at those already-installed
 * locale groups; it never appends the global locale a second time. style2/style3 are
 * asserted byte-identical to the pristine Samsung 00049 payloads.
 */
object GoldenD3Compiler {
    private const val WIDTH = 256
    private const val HEIGHT = 402
    private const val STYLE1 = "style1.bin"

    fun compile(source: Fit3Container): ContainerEdit {
        val pristine = source
        val untouched = listOf("style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }

        val d1 = GoldenD1LayoutCompiler.compile(source)
        val lockedStyle0 = d1.container.entryByBasename("style0.bin").data.copyOf()
        val beforeStyle1 = d1.container.entryByBasename(STYLE1)
        val beforeImages = FaceRecordParser.scanImages(beforeStyle1).size
        val beforeBackground = FaceRecordParser.backgroundImage(beforeStyle1)
            ?: throw Fit3FormatException("$STYLE1: D3 requires a panel background")
        if (beforeBackground.width != WIDTH || beforeBackground.height != HEIGHT) {
            throw Fit3FormatException("$STYLE1: D3 background must be ${WIDTH}x$HEIGHT")
        }

        var current = d1.container
        var changed = d1.changedPayloadBytes

        fun accept(edit: ContainerEdit) {
            current = edit.container
            changed += edit.changedPayloadBytes
        }

        accept(
            FaceEditor.replaceBackgroundInStyle(
                source = current,
                entryBasename = STYLE1,
                width = WIDTH,
                height = HEIGHT,
                argb = GoldenD2CleanPlate.argb(),
            ),
        )

        accept(remapPairAndMove(current, 15, 29, 23, 360, 14, 108, 225))
        accept(remapPairAndMove(current, 16, 48, 101, 360, 15, 132, 225))
        accept(remapPairAndMove(current, 9, 41, 172, 217, 5, 48, 105))

        accept(moveExact(current, 1, WIDGET_COMP, 0, 119, 40, 69, 48))
        accept(moveExact(current, 2, WIDGET_PAIR, 17, 179, 36, 102, 75))

        accept(wireWeatherTextToExistingLocale(current, 164, 333))

        accept(moveExact(current, 8, WIDGET_COMP, 0, 170, 134, 172, 312))
        accept(moveExact(current, 11, WIDGET_COMP, 0, 140, 292, 58, 320))

        val resized = resizeMainTime(current, pristine)
        current = resized.container
        changed += resized.changedPayloadBytes

        accept(moveExact(current, 7, WIDGET_SPRITE, 69, 180, 102, 175, 282))

        if (!lockedStyle0.contentEquals(current.entryByBasename("style0.bin").data)) {
            throw Fit3FormatException("D3 modified approved D1 style0 bytes")
        }
        untouched.forEach { (name, bytes) ->
            if (!bytes.contentEquals(current.entryByBasename(name).data)) {
                throw Fit3FormatException("D3 modified untouched sibling $name")
            }
        }

        val afterStyle1 = current.entryByBasename(STYLE1)
        if (FaceRecordParser.scanImages(afterStyle1).size != beforeImages) {
            throw Fit3FormatException("D3 changed style1 image record count")
        }
        val afterBackground = FaceRecordParser.backgroundImage(afterStyle1)
            ?: throw Fit3FormatException("$STYLE1: D3 lost its panel background")
        if (afterBackground.width != WIDTH || afterBackground.height != HEIGHT) {
            throw Fit3FormatException("$STYLE1: D3 background geometry drifted")
        }

        val report = current.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "D3 compile failed validation: " + report.errors.joinToString { it.code },
            )
        }
        if (current.fileSize >= 4 * 1024 * 1024) {
            throw Fit3FormatException("D3 container exceeds the 4 MiB watch limit")
        }
        if (changed <= 0) {
            throw Fit3FormatException("D3 compile would not change any bytes")
        }
        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin", STYLE1),
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
        val record = FaceRecordParser.scanWidgets(source.entryByBasename(STYLE1)).singleOrNull {
            it.globalIndex == globalIndex &&
                it.widgetType == WIDGET_PAIR &&
                it.sequenceId == oldSequence &&
                it.x == oldX &&
                it.y == oldY
        } ?: throw Fit3FormatException(
            "$STYLE1: D3 Pair g$globalIndex/seq$oldSequence@($oldX,$oldY) missing or ambiguous",
        )
        val expectedBinding = if (globalIndex == 9) 1 else 2
        if ((record.words.getOrNull(1)?.toInt()?.and(0xFF)) != expectedBinding) {
            throw Fit3FormatException("$STYLE1: D3 Pair g$globalIndex binding drifted")
        }

        val remapped = FaceEditor.remapPairSequence(
            source = source,
            entryBasename = STYLE1,
            globalIndex = globalIndex,
            originalSequenceId = oldSequence,
            x = oldX,
            y = oldY,
            newSequenceId = newSequence,
        )
        val moved = FaceEditor.moveWidget(
            source = remapped.container,
            entryBasename = STYLE1,
            globalIndex = globalIndex,
            widgetType = WIDGET_PAIR,
            sequenceId = newSequence,
            x = newX,
            y = newY,
        )
        return ContainerEdit(
            container = moved.container,
            changedPayloadBytes = remapped.changedPayloadBytes + moved.changedPayloadBytes,
            changedStyles = listOf(STYLE1),
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
        FaceRecordParser.scanWidgets(source.entryByBasename(STYLE1)).singleOrNull {
            it.globalIndex == globalIndex &&
                it.widgetType == widgetType &&
                it.sequenceId == sequenceId &&
                it.x == oldX &&
                it.y == oldY
        } ?: throw Fit3FormatException(
            "$STYLE1: D3 widget g$globalIndex/type$widgetType/seq$sequenceId@($oldX,$oldY) missing or ambiguous",
        )
        return FaceEditor.moveWidget(
            source = source,
            entryBasename = STYLE1,
            globalIndex = globalIndex,
            widgetType = widgetType,
            sequenceId = sequenceId,
            x = newX,
            y = newY,
        )
    }

    private fun resizeMainTime(
        source: Fit3Container,
        pristine: Fit3Container,
    ): ContainerEdit {
        val records = FaceRecordParser.scanWidgets(source.entryByBasename(STYLE1))
        listOf(
            intArrayOf(3, 2, 32, 93),
            intArrayOf(4, 3, 86, 93),
            intArrayOf(5, 10, 32, 174),
            intArrayOf(6, 11, 88, 174),
        ).forEach { identity ->
            records.singleOrNull {
                it.globalIndex == identity[0] &&
                    it.widgetType == WIDGET_SPRITE &&
                    it.sequenceId == identity[1] &&
                    it.x == identity[2] &&
                    it.y == identity[3]
            } ?: throw Fit3FormatException(
                "$STYLE1: D3 main-time Sprite g${identity[0]}/seq${identity[1]} missing or ambiguous",
            )
        }

        val resized = StructuralEditor.resizeSprite(
            source = source,
            entryBasenames = listOf(STYLE1),
            sequenceId = 3,
            width = 29,
            height = 69,
            pristine = pristine,
        )
        var current = resized.container
        var changed = resized.changedPayloadBytes
        listOf(
            Triple(3, 2, 64),
            Triple(4, 3, 95),
            Triple(5, 10, 133),
            Triple(6, 11, 171),
        ).forEach { (globalIndex, sequenceId, x) ->
            val moved = FaceEditor.moveWidget(
                source = current,
                entryBasename = STYLE1,
                globalIndex = globalIndex,
                widgetType = WIDGET_SPRITE,
                sequenceId = sequenceId,
                x = x,
                y = 126,
            )
            current = moved.container
            changed += moved.changedPayloadBytes
        }
        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf(STYLE1),
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
                "D3 requires the already-installed 14 AM/PM + 24 weather locale groups",
            )
        }

        val entry = source.entryByBasename(STYLE1)
        val donor = FaceRecordParser.scanWidgets(entry).singleOrNull {
            it.globalIndex == 17 &&
                it.widgetType == WIDGET_PAIR &&
                it.sequenceId == 115 &&
                it.x == 179 &&
                it.y == 360
        } ?: throw Fit3FormatException(
            "$STYLE1: D3 weather-text donor g17/seq115@(179,360) missing or ambiguous",
        )
        if ((donor.words.getOrNull(1)?.toInt()?.and(0xFF)) != 2 ||
            donor.words.getOrNull(2) != 0x0002FFFFL
        ) {
            throw Fit3FormatException("$STYLE1: D3 weather-text donor wiring drifted")
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
            throw Fit3FormatException("D3 weather-text wiring would not change any bytes")
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
                "D3 weather-text wiring failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        return ContainerEdit(
            container = parsed,
            changedPayloadBytes = changed,
            changedStyles = listOf(STYLE1),
        )
    }
}
