package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenHardwareBaselineTest {
    @Test
    fun appliesLayoutOpticalLockAndRealWatchCorrectionsOnlyToSamsung00049() {
        val pristine = real00049()
        val siblings = siblingBytes(pristine)
        val layout = GoldenD1LayoutCompiler.compile(pristine).container
        val optical = GoldenD1OpticalLock.compile(layout).container
        val expected = GoldenD1HardwareCorrections.compile(optical).container

        val actual = GoldenHardwareBaseline.resolve(
            faceId = "00049",
            stock = pristine,
        )

        assertArrayEquals(expected.toByteArray(), actual.toByteArray())
        val records = FaceRecordParser.scanWidgets(actual.entryByBasename("style0.bin"))
        listOf(1, 8, 11).forEach { globalIndex ->
            val composite = records.single {
                it.globalIndex == globalIndex && it.widgetType == WIDGET_COMP
            }
            assertEquals("Composite g$globalIndex", 0xFFB5B6BDL, composite.words[13])
        }

        // Hardware-photo calibration: the firmware adds hidden offsets to these two
        // hour Sprite sequences. These are record coordinates, not the visual target.
        val hourTens = records.single {
            it.globalIndex == 3 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 2
        }
        val hourOnes = records.single {
            it.globalIndex == 4 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 3
        }
        assertEquals(153, hourTens.x)
        assertEquals(139, hourTens.y)
        assertEquals(156, hourOnes.x)
        assertEquals(44, hourOnes.y)

        // Both newly appended Korean strings use the stock WF_WEEK binding because
        // `(목)` was the Korean Pair path proven to render on the real watch.
        val amPm = records.single {
            it.globalIndex == 9 && it.widgetType == WIDGET_PAIR && it.sequenceId == 5
        }
        val weatherText = records.single {
            it.globalIndex == 17 && it.widgetType == WIDGET_PAIR && it.sequenceId == 69
        }
        assertEquals(4, amPm.words[1].toInt() and 0xFF)
        assertEquals(0x0004000CL, amPm.words[2])
        assertEquals(4, weatherText.words[1].toInt() and 0xFF)
        assertEquals(0x0004000EL, weatherText.words[2])
        assertEquals(
            "0d70da8a8047ef439ec43041a737ae02cac28610c34b43708a13d736274d0bc7",
            GoldenD1HardwareCorrections.OUTPUT_PLATE_RGB565_SHA256,
        )

        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, actual.entryByBasename(name).data)
        }
        assertTrue(actual.fileSize < 4 * 1024 * 1024)
        assertTrue(actual.validate().isValid)
    }

    @Test
    fun leavesEveryOtherFaceIdentityUntouched() {
        val pristine = real00049()

        val actual = GoldenHardwareBaseline.resolve(
            faceId = "00003",
            stock = pristine,
        )

        assertSame(pristine, actual)
        assertArrayEquals(pristine.toByteArray(), actual.toByteArray())
    }

    @Test(expected = Fit3FormatException::class)
    fun refusesToApplyGoldenD1Twice() {
        val pristine = real00049()
        val once = GoldenHardwareBaseline.resolve(
            faceId = "00049",
            stock = pristine,
        )

        GoldenHardwareBaseline.resolve(
            faceId = "00049",
            stock = once,
        )
    }

    private fun siblingBytes(source: Fit3Container): Map<String, ByteArray> =
        listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also {
            assertTrue(it.validate().isValid)
        }
    }
}
