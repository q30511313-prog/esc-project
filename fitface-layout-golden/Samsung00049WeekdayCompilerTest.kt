package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049WeekdayCompilerTest {
    @Test
    fun movesOnlyTheNativeKoreanWeekdayPairIntoTheGoldenTarget() {
        val source = real00049()
        val staged = stagePriorGoldenSemantics(source)
        val untouched = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { staged.entryByBasename(it).data.copyOf() }

        val before = FaceRecordParser.scanWidgets(staged.entryByBasename("style0.bin"))
            .single {
                it.globalIndex == 2 &&
                    it.widgetType == WIDGET_PAIR &&
                    it.sequenceId == 17
            }
        assertEquals(179, before.x)
        assertEquals(36, before.y)
        assertEquals(4, before.words.getValue(1).toInt() and 0xFF)
        val bindingWord = before.words.getValue(1)

        val result = GoldenSemanticCompiler.compileWeekday(
            source = staged,
            entryBasename = "style0.bin",
            x = 107,
            y = 80,
        )

        val edited = result.container
        val after = FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
            .single {
                it.globalIndex == 2 &&
                    it.widgetType == WIDGET_PAIR &&
                    it.sequenceId == 17
            }
        assertEquals(107, after.x)
        assertEquals(80, after.y)
        assertEquals(66, after.width)
        assertEquals(28, after.height)
        assertEquals(bindingWord, after.words.getValue(1))

        // Previously proven style0 semantics remain live.
        assertEquals(1, FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
            .count { it.widgetType == WIDGET_PAIR && it.sequenceId == 5 })
        assertEquals(1, FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
            .count { it.widgetType == WIDGET_PAIR && it.sequenceId == 14 })
        assertEquals(1, FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
            .count { it.widgetType == WIDGET_PAIR && it.sequenceId == 15 })
        val date = FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
            .single { it.globalIndex == 1 && it.widgetType == WIDGET_COMP && it.sequenceId == 0 }
        assertEquals(65, date.x)
        assertEquals(47, date.y)

        assertEquals(listOf("style0.bin"), result.changedStyles.distinct())
        assertTrue(result.changedPayloadBytes > 0)
        untouched.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edited.entryByBasename(name).data)
        }
        assertEquals(staged.fileSize, edited.fileSize)
        assertTrue(edited.validate().isValid)
    }

    @Test
    fun weekdayMoveFailsClosedIfTheNativeIdentityWasAlreadyChanged() {
        val source = real00049()
        val staged = stagePriorGoldenSemantics(source)
        val movedOnce = FaceEditor.moveWidget(
            source = staged,
            entryBasename = "style0.bin",
            globalIndex = 2,
            widgetType = WIDGET_PAIR,
            sequenceId = 17,
            x = 107,
            y = 80,
        ).container

        try {
            GoldenSemanticCompiler.compileWeekday(
                source = movedOnce,
                entryBasename = "style0.bin",
                x = 107,
                y = 80,
            )
            throw AssertionError("expected fail-closed weekday identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden weekday"))
        }
    }

    private fun stagePriorGoldenSemantics(source: Fit3Container): Fit3Container {
        val seconds = GoldenSemanticCompiler.compileSeconds(
            source = source,
            entryBasename = "style0.bin",
            tensX = 48,
            onesX = 72,
            y = 257,
        ).container
        val amPm = GoldenSemanticCompiler.compileAmPm(
            source = seconds,
            entryBasename = "style0.bin",
            x = 48,
            y = 120,
        ).container
        return GoldenDateCompiler.compile(
            source = amPm,
            entryBasename = "style0.bin",
            targetX = 65,
            targetY = 47,
        ).edit.container
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
