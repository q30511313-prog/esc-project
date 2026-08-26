package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049SecondsCompilerTest {
    @Test
    fun style0RepurposesTwoNumericPairsAsIndependentLiveSeconds() {
        val source = real00049()
        val beforeStyle0 = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin"))
        val tensDonor = beforeStyle0.single {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 15 &&
                it.sequenceId == 29 &&
                it.x == 23 &&
                it.y == 360
        }
        val onesDonor = beforeStyle0.single {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 16 &&
                it.sequenceId == 48 &&
                it.x == 101 &&
                it.y == 360
        }
        assertEquals(2, tensDonor.words[1].toInt() and 0xFF)
        assertEquals(2, onesDonor.words[1].toInt() and 0xFF)

        val untouched = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }

        val edit = GoldenSemanticCompiler.compileSeconds(
            source = source,
            entryBasename = "style0.bin",
            tensX = 48,
            onesX = 72,
            y = 257,
        )

        val afterStyle0 = FaceRecordParser.scanWidgets(
            edit.container.entryByBasename("style0.bin"),
        )
        val tens = afterStyle0.single {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 15 &&
                it.sequenceId == 14
        }
        val ones = afterStyle0.single {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 16 &&
                it.sequenceId == 15
        }

        assertEquals(48, tens.x)
        assertEquals(257, tens.y)
        assertEquals(72, ones.x)
        assertEquals(257, ones.y)
        assertEquals(2, tens.words[1].toInt() and 0xFF)
        assertEquals(2, ones.words[1].toInt() and 0xFF)
        assertEquals(
            tensDonor.words[1] and 0xFFFF_FF00L,
            tens.words[1] and 0xFFFF_FF00L,
        )
        assertEquals(
            onesDonor.words[1] and 0xFFFF_FF00L,
            ones.words[1] and 0xFFFF_FF00L,
        )
        assertEquals(0, afterStyle0.count {
            it.globalIndex == 15 && it.sequenceId == 29
        })
        assertEquals(0, afterStyle0.count {
            it.globalIndex == 16 && it.sequenceId == 48
        })

        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        assertTrue(edit.changedPayloadBytes > 0)
        untouched.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edit.container.entryByBasename(name).data)
        }
        assertEquals(source.fileSize, edit.container.fileSize)
        assertTrue(edit.container.validate().isValid)
    }

    @Test
    fun refusesAnythingExceptTheKnownPristine00049DonorIdentity() {
        val source = real00049()
        val first = FaceEditor.remapPairSequence(
            source = source,
            entryBasename = "style0.bin",
            globalIndex = 15,
            originalSequenceId = 29,
            x = 23,
            y = 360,
            newSequenceId = 14,
        ).container

        try {
            GoldenSemanticCompiler.compileSeconds(
                source = first,
                entryBasename = "style0.bin",
                tensX = 48,
                onesX = 72,
                y = 257,
            )
            throw AssertionError("expected fail-closed donor identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden seconds donor"))
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
