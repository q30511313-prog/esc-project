package dev.fitface.studio.core.format

enum class GoldenDateMode {
    INDEPENDENT_PARTS,
    STOCK_COMPOSITE_FALLBACK,
}

data class GoldenDateCompileResult(
    val mode: GoldenDateMode,
    val edit: ContainerEdit,
)

/**
 * Golden date compiler for the real Samsung 00049 style0 inventory.
 *
 * The preferred design asks for independent year/month/day values (24/21/18), but
 * after the already-proven seconds and AM/PM allocations the stock face has only one
 * free numeric Pair donor. The safe Golden path therefore keeps the native live date
 * Composite and repositions it. No widget or image record is appended here.
 */
object GoldenDateCompiler {
    fun compile(
        source: Fit3Container,
        entryBasename: String,
        targetX: Int,
        targetY: Int,
    ): GoldenDateCompileResult {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden date contract is defined only for style0.bin",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val records = FaceRecordParser.scanWidgets(entry)

        // Fail closed against the exact pristine native date identity observed in
        // Samsung 00049 v4.0.2. If another stage already changed it, this compiler must
        // not silently reinterpret an arbitrary Composite as the stock date.
        records.singleOrNull {
            it.globalIndex == 1 &&
                it.widgetType == WIDGET_COMP &&
                it.sequenceId == 0 &&
                it.x == 119 &&
                it.y == 40 &&
                it.width == 60 &&
                it.height == 28
        } ?: throw Fit3FormatException(
            "Golden date Composite g1/seq0@(119,40) 60x28 is missing or ambiguous",
        )

        // Numeric Pair donors are binding-low-byte 2. Seconds already occupy 14/15;
        // those are not free. On the real 00049 pipeline this leaves only g17/seq115.
        val freeNumericPairs = records.filter {
            it.widgetType == WIDGET_PAIR &&
                it.words.getOrNull(1)?.toInt()?.and(0xFF) == 2 &&
                it.sequenceId !in setOf(14, 15)
        }

        if (freeNumericPairs.size >= 3) {
            // Do not guess which three records should become 24/21/18. That path needs
            // its own explicit donor identity contract and hardware proof.
            throw Fit3FormatException(
                "independent Golden date donors require an explicit approved 24/21/18 contract",
            )
        }

        val moved = FaceEditor.moveWidget(
            source = source,
            entryBasename = entryBasename,
            globalIndex = 1,
            widgetType = WIDGET_COMP,
            sequenceId = 0,
            x = targetX,
            y = targetY,
        )

        return GoldenDateCompileResult(
            mode = GoldenDateMode.STOCK_COMPOSITE_FALLBACK,
            edit = moved,
        )
    }
}
