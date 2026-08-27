package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049TempBatteryCompilerTest {
    @Test
    fun movesNativeLiveTemperatureAndBatteryPercentWithoutChangingTheirSemantics() {
        val staged = stageGoldenPrerequisites(real00049())
        val before = FaceRecordParser.scanWidgets(staged.entryByBasename("style0.bin"))
        val tempBefore = before.single { it.globalIndex == 8 && it.widgetType == WIDGET_COMP }
        val batteryBefore = before.single { it.globalIndex == 11 && it.widgetType == WIDGET_COMP }
        val gaugeBefore = before.single { it.globalIndex == 10 && it.widgetType == WIDGET_BADGE && it.sequenceId == 37 }
        val siblingStyles = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { staged.entryByBasename(it).data.copyOf() }

        assertEquals(0xFFFF003EL, tempBefore.words[0]) // live temperature source 62
        assertEquals(0xFFFF0025L, batteryBefore.words[0]) // live battery source 37

        val edit = GoldenSemanticCompiler.compileTempBattery(
            source = staged,
            entryBasename = "style0.bin",
            tempX = 171,
            tempY = 260,
            batteryPercentX = 82,
            batteryPercentY = 336,
        )

        val after = FaceRecordParser.scanWidgets(edit.container.entryByBasename("style0.bin"))
        val tempAfter = after.single { it.globalIndex == 8 && it.widgetType == WIDGET_COMP }
        val batteryAfter = after.single { it.globalIndex == 11 && it.widgetType == WIDGET_COMP }
        val gaugeAfter = after.single { it.globalIndex == 10 && it.widgetType == WIDGET_BADGE && it.sequenceId == 37 }

        assertEquals(171, tempAfter.x)
        assertEquals(260, tempAfter.y)
        assertEquals(51, tempAfter.width)
        assertEquals(22, tempAfter.height)
        assertEquals(tempBefore.words, tempAfter.words)

        assertEquals(82, batteryAfter.x)
        assertEquals(336, batteryAfter.y)
        assertEquals(55, batteryAfter.width)
        assertEquals(19, batteryAfter.height)
        assertEquals(batteryBefore.words, batteryAfter.words)

        // The stock dynamic Badge is not reshaped into the mockup's battery icon.
        // The final icon outline belongs to the clean plate; this stage leaves the
        // native gauge byte semantics untouched.
        assertEquals(gaugeBefore, gaugeAfter)

        siblingStyles.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edit.container.entryByBasename(name).data)
        }
        assertTrue(edit.container.validate().isValid)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        assertTrue(edit.changedPayloadBytes > 0)
    }

    @Test
    fun failsClosedWhenNativeTemperatureIdentityWasAlreadyModified() {
        val staged = stageGoldenPrerequisites(real00049())
        val moved = FaceEditor.moveWidget(
            source = staged,
            entryBasename = "style0.bin",
            globalIndex = 8,
            widgetType = WIDGET_COMP,
            sequenceId = 0,
            x = 160,
            y = 150,
        ).container

        try {
            GoldenSemanticCompiler.compileTempBattery(
                source = moved,
                entryBasename = "style0.bin",
                tempX = 171,
                tempY = 260,
                batteryPercentX = 82,
                batteryPercentY = 336,
            )
            throw AssertionError("expected fail-closed temperature identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden temperature"))
        }
    }

    private fun stageGoldenPrerequisites(source: Fit3Container): Fit3Container {
        var current = GoldenSemanticCompiler.compileSeconds(
            source = source,
            entryBasename = "style0.bin",
            tensX = 48,
            onesX = 72,
            y = 257,
        ).container
        current = GoldenSemanticCompiler.compileAmPm(
            source = current,
            entryBasename = "style0.bin",
            x = 48,
            y = 120,
        ).container
        current = GoldenDateCompiler.compile(
            source = current,
            entryBasename = "style0.bin",
            targetX = 65,
            targetY = 47,
        ).edit.container
        current = GoldenSemanticCompiler.compileWeekday(
            source = current,
            entryBasename = "style0.bin",
            x = 107,
            y = 80,
        ).container
        current = GoldenWeatherTextEditor.wire00049(
            source = current,
            entryBasename = "style0.bin",
            x = 112,
            y = 301,
        ).container
        return current
    }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also {
            assertTrue(it.validate().isValid)
        }
    }
}
