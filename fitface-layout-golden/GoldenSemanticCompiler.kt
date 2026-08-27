package dev.fitface.studio.core.format

/**
 * Compiles the first Golden-layout live semantics into Samsung 00049 style0.
 *
 * This deliberately fails closed against the exact pristine donor identities proven
 * by the Golden compiler tests. It does not create new records, resize the container,
 * or touch sibling styles.
 */
object GoldenSemanticCompiler {
    fun compileWeekday(
        source: Fit3Container,
        entryBasename: String,
        x: Int,
        y: Int,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden weekday contract is defined only for style0.bin",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val donor = FaceRecordParser.scanWidgets(entry).singleOrNull {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 2 &&
                it.sequenceId == 17 &&
                it.x == 179 &&
                it.y == 36 &&
                it.width == 66 &&
                it.height == 28
        } ?: throw Fit3FormatException(
            "Golden weekday Pair g2/seq17@(179,36) 66x28 is missing or ambiguous",
        )
        val bindingWord = donor.words.getOrNull(1) ?: throw Fit3FormatException(
            "Golden weekday Pair g2 has no binding/layout word",
        )
        if ((bindingWord.toInt() and 0xFF) != 4) {
            throw Fit3FormatException(
                "Golden weekday Pair g2 must retain WF_WEEK binding 4",
            )
        }

        return FaceEditor.moveWidget(
            source = source,
            entryBasename = entryBasename,
            globalIndex = 2,
            widgetType = WIDGET_PAIR,
            sequenceId = 17,
            x = x,
            y = y,
        )
    }

    fun compileAmPm(
        source: Fit3Container,
        entryBasename: String,
        x: Int,
        y: Int,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden AM/PM donor contract is defined only for style0.bin",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val donor = FaceRecordParser.scanWidgets(entry).singleOrNull {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 9 &&
                it.sequenceId == 41 &&
                it.x == 172 &&
                it.y == 217
        } ?: throw Fit3FormatException(
            "Golden AM/PM donor g9/seq41@(172,217) is missing or ambiguous",
        )
        val bindingWord = donor.words.getOrNull(1) ?: throw Fit3FormatException(
            "Golden AM/PM donor g9 has no Pair binding/layout word",
        )
        if ((bindingWord.toInt() and 0xFF) != 1 ||
            donor.words.getOrNull(2) != 0x0001FFFFL
        ) {
            throw Fit3FormatException(
                "Golden AM/PM donor g9 must retain pristine binding1/FFFF locale wiring",
            )
        }

        val locale = GoldenAmPmLocaleEditor.wire00049(
            source = source,
            entryBasename = entryBasename,
        )
        val semantic = FaceEditor.remapPairSequence(
            source = locale.container,
            entryBasename = entryBasename,
            globalIndex = 9,
            originalSequenceId = 41,
            x = 172,
            y = 217,
            newSequenceId = 5,
        )
        val moved = FaceEditor.moveWidget(
            source = semantic.container,
            entryBasename = entryBasename,
            globalIndex = 9,
            widgetType = WIDGET_PAIR,
            sequenceId = 5,
            x = x,
            y = y,
        )
        return ContainerEdit(
            container = moved.container,
            changedPayloadBytes = locale.changedPayloadBytes +
                semantic.changedPayloadBytes + moved.changedPayloadBytes,
            changedStyles = listOf(entryBasename),
        )
    }

    fun compileTempBattery(
        source: Fit3Container,
        entryBasename: String,
        tempX: Int,
        tempY: Int,
        batteryPercentX: Int,
        batteryPercentY: Int,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden temperature/battery contract is defined only for style0.bin",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val records = FaceRecordParser.scanWidgets(entry)
        val temperature = records.singleOrNull {
            it.globalIndex == 8 &&
                it.widgetType == WIDGET_COMP &&
                it.sequenceId == 0 &&
                it.x == 170 &&
                it.y == 134 &&
                it.width == 51 &&
                it.height == 22 &&
                it.words.firstOrNull() == 0xFFFF003EL
        } ?: throw Fit3FormatException(
            "Golden temperature Composite g8/source62@(170,134) 51x22 is missing or ambiguous",
        )
        val battery = records.singleOrNull {
            it.globalIndex == 11 &&
                it.widgetType == WIDGET_COMP &&
                it.sequenceId == 0 &&
                it.x == 140 &&
                it.y == 292 &&
                it.width == 55 &&
                it.height == 19 &&
                it.words.firstOrNull() == 0xFFFF0025L
        } ?: throw Fit3FormatException(
            "Golden battery Composite g11/source37@(140,292) 55x19 is missing or ambiguous",
        )
        records.singleOrNull {
            it.globalIndex == 10 &&
                it.widgetType == WIDGET_BADGE &&
                it.sequenceId == 37 &&
                it.x == 34 &&
                it.y == 301
        } ?: throw Fit3FormatException(
            "Golden battery Badge g10/seq37@(34,301) is missing or ambiguous",
        )

        val movedTemp = FaceEditor.moveWidget(
            source = source,
            entryBasename = entryBasename,
            globalIndex = temperature.globalIndex,
            widgetType = temperature.widgetType,
            sequenceId = temperature.sequenceId,
            x = tempX,
            y = tempY,
        )
        val movedBattery = FaceEditor.moveWidget(
            source = movedTemp.container,
            entryBasename = entryBasename,
            globalIndex = battery.globalIndex,
            widgetType = battery.widgetType,
            sequenceId = battery.sequenceId,
            x = batteryPercentX,
            y = batteryPercentY,
        )
        return ContainerEdit(
            container = movedBattery.container,
            changedPayloadBytes = movedTemp.changedPayloadBytes + movedBattery.changedPayloadBytes,
            changedStyles = listOf(entryBasename),
        )
    }

    fun compileMainTime(
        source: Fit3Container,
        pristine: Fit3Container,
        entryBasename: String,
        digitWidth: Int,
        digitHeight: Int,
        hourTensX: Int,
        hourOnesX: Int,
        minuteTensX: Int,
        minuteOnesX: Int,
        y: Int,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden main time contract is defined only for style0.bin",
            )
        }

        val records = FaceRecordParser.scanWidgets(source.entryByBasename(entryBasename))
        val pristineIdentities = listOf(
            listOf(3, 2, 32, 93),
            listOf(4, 3, 86, 93),
            listOf(5, 10, 32, 174),
            listOf(6, 11, 88, 174),
        )
        pristineIdentities.forEach { identity ->
            val globalIndex = identity[0]
            val sequenceId = identity[1]
            val x = identity[2]
            val originalY = identity[3]
            records.singleOrNull {
                it.widgetType == WIDGET_SPRITE &&
                    it.globalIndex == globalIndex &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == originalY
            } ?: throw Fit3FormatException(
                "Golden main time Sprite g$globalIndex/seq$sequenceId@($x,$originalY) is missing or ambiguous",
            )
        }

        // Sequence 3 reaches all ten digit records; resizeSprite closes over every
        // other Sprite sharing those image records (2/10/11), so the pool is rewritten
        // exactly once while unrelated weather frames remain untouched.
        val resized = StructuralEditor.resizeSprite(
            source = source,
            entryBasenames = listOf(entryBasename),
            sequenceId = 3,
            width = digitWidth,
            height = digitHeight,
            pristine = pristine,
        )

        var current = resized.container
        var changed = resized.changedPayloadBytes
        val targets = listOf(
            Triple(3, 2, hourTensX),
            Triple(4, 3, hourOnesX),
            Triple(5, 10, minuteTensX),
            Triple(6, 11, minuteOnesX),
        )
        targets.forEach { (globalIndex, sequenceId, x) ->
            val moved = FaceEditor.moveWidget(
                source = current,
                entryBasename = entryBasename,
                globalIndex = globalIndex,
                widgetType = WIDGET_SPRITE,
                sequenceId = sequenceId,
                x = x,
                y = y,
            )
            current = moved.container
            changed += moved.changedPayloadBytes
        }

        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf(entryBasename),
        )
    }

    fun compileSeconds(
        source: Fit3Container,
        entryBasename: String,
        tensX: Int,
        onesX: Int,
        y: Int,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden seconds donor contract is defined only for style0.bin",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val widgets = FaceRecordParser.scanWidgets(entry)
        val tens = widgets.singleOrNull {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 15 &&
                it.sequenceId == 29 &&
                it.x == 23 &&
                it.y == 360
        } ?: throw Fit3FormatException(
            "Golden seconds donor g15/seq29@(23,360) is missing or ambiguous",
        )
        val ones = widgets.singleOrNull {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 16 &&
                it.sequenceId == 48 &&
                it.x == 101 &&
                it.y == 360
        } ?: throw Fit3FormatException(
            "Golden seconds donor g16/seq48@(101,360) is missing or ambiguous",
        )

        fun requireNumericBinding(label: String, record: WidgetRecord) {
            val bindingWord = record.words.getOrNull(1) ?: throw Fit3FormatException(
                "Golden seconds donor $label has no Pair binding/layout word",
            )
            if ((bindingWord.toInt() and 0xFF) != 2) {
                throw Fit3FormatException(
                    "Golden seconds donor $label must retain numeric binding 2",
                )
            }
        }
        requireNumericBinding("g15", tens)
        requireNumericBinding("g16", ones)

        var current = source
        var changed = 0

        val tensSemantic = FaceEditor.remapPairSequence(
            source = current,
            entryBasename = entryBasename,
            globalIndex = 15,
            originalSequenceId = 29,
            x = 23,
            y = 360,
            newSequenceId = 14,
        )
        current = tensSemantic.container
        changed += tensSemantic.changedPayloadBytes

        val tensMove = FaceEditor.moveWidget(
            source = current,
            entryBasename = entryBasename,
            globalIndex = 15,
            widgetType = WIDGET_PAIR,
            sequenceId = 14,
            x = tensX,
            y = y,
        )
        current = tensMove.container
        changed += tensMove.changedPayloadBytes

        val onesSemantic = FaceEditor.remapPairSequence(
            source = current,
            entryBasename = entryBasename,
            globalIndex = 16,
            originalSequenceId = 48,
            x = 101,
            y = 360,
            newSequenceId = 15,
        )
        current = onesSemantic.container
        changed += onesSemantic.changedPayloadBytes

        val onesMove = FaceEditor.moveWidget(
            source = current,
            entryBasename = entryBasename,
            globalIndex = 16,
            widgetType = WIDGET_PAIR,
            sequenceId = 15,
            x = onesX,
            y = y,
        )
        current = onesMove.container
        changed += onesMove.changedPayloadBytes

        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf(entryBasename),
        )
    }
}
