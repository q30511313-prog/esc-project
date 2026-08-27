package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenHardwareBaselineTest {
    @Test
    fun appliesFullGoldenD1LayoutThenOpticalLockOnlyToSamsung00049() {
        val pristine = real00049()
        val siblings = siblingBytes(pristine)
        val layout = GoldenD1LayoutCompiler.compile(pristine).container
        val expected = GoldenD1OpticalLock.compile(layout).container

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
