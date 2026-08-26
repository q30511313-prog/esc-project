package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049AmPmCompilerTest {
    @Test
    fun style0RepurposesTextPairAsLiveAmPmWithoutDisturbingSecondsOrSiblingStyles() {
        val source = real00049()
        val pristineStyle0 = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin"))
        val donor = pristineStyle0.single {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 9 &&
                it.sequenceId == 41 &&
                it.x == 172 &&
                it.y == 217
        }
        assertEquals(1, donor.words[1].toInt() and 0xFF)

        val untouched = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }

        val withSeconds = GoldenSemanticCompiler.compileSeconds(
            source = source,
            entryBasename = "style0.bin",
            tensX = 48,
            onesX = 72,
            y = 257,
        ).container

        val edit = GoldenSemanticCompiler.compileAmPm(
            source = withSeconds,
            entryBasename = "style0.bin",
            x = 48,
            y = 120,
        )

        val after = FaceRecordParser.scanWidgets(
            edit.container.entryByBasename("style0.bin"),
        )
        val amPm = after.single {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 9 &&
                it.sequenceId == 5
        }
        assertEquals(48, amPm.x)
        assertEquals(120, amPm.y)
        assertEquals(1, amPm.words[1].toInt() and 0xFF)
        assertEquals(
            donor.words[1] and 0xFFFF_FF00L,
            amPm.words[1] and 0xFFFF_FF00L,
        )
        assertEquals(0, after.count {
            it.globalIndex == 9 && it.sequenceId == 41
        })

        val secondsTens = after.single {
            it.widgetType == WIDGET_PAIR && it.globalIndex == 15 && it.sequenceId == 14
        }
        val secondsOnes = after.single {
            it.widgetType == WIDGET_PAIR && it.globalIndex == 16 && it.sequenceId == 15
        }
        assertEquals(48, secondsTens.x)
        assertEquals(257, secondsTens.y)
        assertEquals(72, secondsOnes.x)
        assertEquals(257, secondsOnes.y)

        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        assertTrue(edit.changedPayloadBytes > 0)
        untouched.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edit.container.entryByBasename(name).data)
        }
        assertEquals(source.fileSize, edit.container.fileSize)
        assertTrue(edit.container.validate().isValid)
    }

    @Test
    fun refusesAnythingExceptTheKnownPristine00049AmPmDonorIdentity() {
        val source = real00049()
        val altered = FaceEditor.remapPairSequence(
            source = source,
            entryBasename = "style0.bin",
            globalIndex = 9,
            originalSequenceId = 41,
            x = 172,
            y = 217,
            newSequenceId = 5,
        ).container

        try {
            GoldenSemanticCompiler.compileAmPm(
                source = altered,
                entryBasename = "style0.bin",
                x = 48,
                y = 120,
            )
            throw AssertionError("expected fail-closed AM/PM donor identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden AM/PM donor"))
        }
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
