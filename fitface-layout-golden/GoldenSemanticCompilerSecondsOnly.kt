package dev.fitface.studio.core.format

/** TDD baseline containing only the already-proven Golden live-seconds compiler. */
object GoldenSemanticCompiler {
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
