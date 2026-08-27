package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD2HardwareBaselineTest {
    @Test
    fun appliesApprovedD2OnlyToSamsung00049() {
        val pristine = real00049()
        val siblings = siblingBytes(pristine)
        val expected = GoldenD2LayoutCompiler.compile(pristine).container

        val actual = GoldenD2HardwareBaseline.resolve("00049", pristine)

        assertArrayEquals(expected.toByteArray(), actual.toByteArray())
        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, actual.entryByBasename(name).data)
        }
        assertTrue(actual.fileSize < 4 * 1024 * 1024)
        assertTrue(actual.validate().isValid)
    }

    @Test
    fun leavesEveryOtherFaceIdentityUntouched() {
        val pristine = real00049()
        val actual = GoldenD2HardwareBaseline.resolve("00003", pristine)
        assertSame(pristine, actual)
        assertArrayEquals(pristine.toByteArray(), actual.toByteArray())
    }

    @Test(expected = Fit3FormatException::class)
    fun refusesToApplyD2Twice() {
        val pristine = real00049()
        val once = GoldenD2HardwareBaseline.resolve("00049", pristine)
        GoldenD2HardwareBaseline.resolve("00049", once)
    }

    private fun siblingBytes(source: Fit3Container): Map<String, ByteArray> =
        listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also { assertTrue(it.validate().isValid) }
    }
}
