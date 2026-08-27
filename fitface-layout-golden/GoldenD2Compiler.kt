package dev.fitface.studio.core.format

/**
 * Design-2 semantic transaction for approved 1000028943 artwork.
 *
 * Reuses only the already-proven Samsung 00049 semantic editors, changing their
 * style0 placement geometry for D2. Sibling styles remain outside every target.
 */
object GoldenD2Compiler {
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
                tensX = 108,
                onesX = 132,
                y = 225,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileAmPm(
                source = current,
                entryBasename = "style0.bin",
                x = 48,
                y = 105,
            ),
        )
        accept(
            GoldenDateCompiler.compile(
                source = current,
                entryBasename = "style0.bin",
                targetX = 69,
                targetY = 48,
            ).edit,
        )
        accept(
            GoldenSemanticCompiler.compileWeekday(
                source = current,
                entryBasename = "style0.bin",
                x = 102,
                y = 75,
            ),
        )
        accept(
            GoldenWeatherTextEditor.wire00049(
                source = current,
                entryBasename = "style0.bin",
                x = 164,
                y = 333,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileTempBattery(
                source = current,
                entryBasename = "style0.bin",
                tempX = 172,
                tempY = 312,
                batteryPercentX = 58,
                batteryPercentY = 320,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileMainTime(
                source = current,
                pristine = pristine,
                entryBasename = "style0.bin",
                digitWidth = 29,
                digitHeight = 69,
                hourTensX = 64,
                hourOnesX = 95,
                minuteTensX = 133,
                minuteOnesX = 171,
                y = 126,
            ),
        )
        accept(
            GoldenSemanticCompiler.compileWeatherIcon(
                source = current,
                entryBasename = "style0.bin",
                x = 175,
                y = 282,
            ),
        )

        val report = current.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden D2 compile failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }
        if (changed <= 0) {
            throw Fit3FormatException("Golden D2 compile would not change any bytes")
        }
        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin"),
        )
    }
}
