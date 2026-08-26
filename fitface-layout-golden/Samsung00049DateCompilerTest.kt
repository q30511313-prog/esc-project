package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049DateCompilerTest {
    @Test
    fun actual00049SelectsStockCompositeFallbackWhenThreeNumericPairsAreUnavailable() {
        val source = real00049()
        val staged = stageSecondsAndAmPm(source)
        val before = FaceRecordParser.scanWidgets(staged.entryByBasename("style0.bin"))

        val freeNumericPairs = before.filter {
            it.widgetType == WIDGET_PAIR &&
                (it.words.getOrNull(1)?.toInt()?.and(0xFF) == 2) &&
                it.sequenceId !in setOf(14, 15)
        }
        assertEquals(1, freeNumericPairs.size)
        assertEquals(17, freeNumericPairs.single().globalIndex)
        assertEquals(115, freeNumericPairs.single().sequenceId)

        val untouched = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { staged.entryByBasename(it).data.copyOf() }

        val result = GoldenDateCompiler.compile(
            source = staged,
            entryBasename = "style0.bin",
            targetX = 65,
            targetY = 47,
        )

        assertEquals(GoldenDateMode.STOCK_COMPOSITE_FALLBACK, result.mode)
        val edited = result.edit.container
        val after = FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
        val date = after.single {
            it.globalIndex == 1 && it.widgetType == WIDGET_COMP && it.sequenceId == 0
        }
        assertEquals(65, date.x)
        assertEquals(47, date.y)
        assertEquals(60, date.width)
        assertEquals(28, date.height)

        // Independent 24/21/18 Pair values are deliberately not fabricated when
        // the real stock face does not have three compatible donors left.
        assertEquals(0, after.count {
            it.widgetType == WIDGET_PAIR && it.sequenceId in setOf(24, 21, 18)
        })

        // Earlier proven live semantics survive the fallback date move.
        assertEquals(1, after.count { it.widgetType == WIDGET_PAIR && it.sequenceId == 5 })
        assertEquals(1, after.count { it.widgetType == WIDGET_PAIR && it.sequenceId == 14 })
        assertEquals(1, after.count { it.widgetType == WIDGET_PAIR && it.sequenceId == 15 })
        assertEquals(1, after.count { it.widgetType == WIDGET_PAIR && it.sequenceId == 17 })

        assertEquals(listOf("style0.bin"), result.edit.changedStyles.distinct())
        assertTrue(result.edit.changedPayloadBytes > 0)
        untouched.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edited.entryByBasename(name).data)
        }
        assertEquals(source.fileSize, edited.fileSize)
        assertTrue(edited.validate().isValid)
    }

    @Test
    fun fallbackFailsClosedIfTheNativeDateCompositeIdentityIsNotPristine() {
        val source = real00049()
        val staged = stageSecondsAndAmPm(source)
        val movedOnce = FaceEditor.moveWidget(
            source = staged,
            entryBasename = "style0.bin",
            globalIndex = 1,
            widgetType = WIDGET_COMP,
            sequenceId = 0,
            x = 65,
            y = 47,
        ).container

        try {
            GoldenDateCompiler.compile(
                source = movedOnce,
                entryBasename = "style0.bin",
                targetX = 65,
                targetY = 47,
            )
            throw AssertionError("expected fail-closed native date identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden date Composite"))
        }
    }

    private fun stageSecondsAndAmPm(source: Fit3Container): Fit3Container {
        val seconds = GoldenSemanticCompiler.compileSeconds(
            source = source,
            entryBasename = "style0.bin",
            tensX = 48,
            onesX = 72,
            y = 257,
        ).container
        return GoldenSemanticCompiler.compileAmPm(
            source = seconds,
            entryBasename = "style0.bin",
            x = 48,
            y = 120,
        ).container
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
