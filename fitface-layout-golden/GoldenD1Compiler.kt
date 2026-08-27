package dev.fitface.studio.core.format

/**
 * Applies the already-proven Samsung 00049 D1 live semantic edits as one fail-closed
 * transaction. The caller supplies the pristine 00049 container; sibling styles are
 * never targeted and no widget/image record is fabricated.
 */
object GoldenD1Compiler {
    fun compile(source: Fit3Container): ContainerEdit {
        val pristine = source
        var current = source
        var changed = 0

        fun accept(edit: ContainerEdit) {
            current = edit.container
            changed += edit.changedPayloadBytes
        }

        accept(
            GoldenSemanticCompiler.compileSeconds(
                source = current,
                entryBasename = "style0.bin",
                tensX = 48,
                onesX = 72,
                y = 257,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileAmPm(
                source = current,
                entryBasename = "style0.bin",
                x = 48,
                y = 120,
            ),
        )
        accept(
            GoldenDateCompiler.compile(
                source = current,
                entryBasename = "style0.bin",
                targetX = 65,
                targetY = 47,
            ).edit,
        )
        accept(
            GoldenSemanticCompiler.compileWeekday(
                source = current,
                entryBasename = "style0.bin",
                x = 107,
                y = 80,
            ),
        )
        accept(
            GoldenWeatherTextEditor.wire00049(
                source = current,
                entryBasename = "style0.bin",
                x = 112,
                y = 301,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileTempBattery(
                source = current,
                entryBasename = "style0.bin",
                tempX = 171,
                tempY = 260,
                batteryPercentX = 82,
                batteryPercentY = 336,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileMainTime(
                source = current,
                pristine = pristine,
                entryBasename = "style0.bin",
                digitWidth = 27,
                digitHeight = 67,
                hourTensX = 77,
                hourOnesX = 106,
                minuteTensX = 142,
                minuteOnesX = 171,
                y = 139,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileWeatherIcon(
                source = current,
                entryBasename = "style0.bin",
                x = 113,
                y = 261,
            ),
        )

        val report = current.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden D1 compile failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        if (changed <= 0) {
            throw Fit3FormatException("Golden D1 compile would not change any bytes")
        }

        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin"),
        )
    }
}
