package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenHardwareBaselineTest {
    @Test
    fun appliesGoldenD1OnlyToSamsung00049() {
        val pristine = real00049()
        val expected = GoldenD1Compiler.compile(pristine).container

        val actual = GoldenHardwareBaseline.resolve(
            faceId = "00049",
            stock = pristine,
        )

        assertArrayEquals(expected.toByteArray(), actual.toByteArray())
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

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also {
            assertTrue(it.validate().isValid)
        }
    }
}
