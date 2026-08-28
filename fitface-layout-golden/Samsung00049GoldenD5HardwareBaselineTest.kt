package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD5HardwareBaselineTest {
    @Test
    fun locksApprovedStyle0HardwareWhilePreservingD5Styles1To3() {
        val pristine = real00049()
        val logical = GoldenD5Compiler.compile(pristine).container
        val expectedStyle0 = GoldenHardwareBaseline.resolve("00049", pristine)
            .entryByBasename("style0.bin").data
        val expectedStyle1 = logical.entryByBasename("style1.bin").data.copyOf()
        val expectedStyle2 = logical.entryByBasename("style2.bin").data.copyOf()
        val expectedStyle3 = logical.entryByBasename("style3.bin").data.copyOf()

        assertFalse(
            "D5 logical style3 must differ from pristine",
            pristine.entryByBasename("style3.bin").data.contentEquals(expectedStyle3),
        )

        val resolved = GoldenD5HardwareBaseline.resolve("00049", pristine)
        assertTrue(resolved.validate().isValid)
        assertTrue(resolved.fileSize < 4 * 1024 * 1024)
        assertArrayEquals(expectedStyle0, resolved.entryByBasename("style0.bin").data)
        assertArrayEquals(expectedStyle1, resolved.entryByBasename("style1.bin").data)
        assertArrayEquals(expectedStyle2, resolved.entryByBasename("style2.bin").data)
        assertArrayEquals(expectedStyle3, resolved.entryByBasename("style3.bin").data)
    }

    @Test
    fun leavesNonTargetFaceByIdentity() {
        val pristine = real00049()
        assertSame(pristine, GoldenD5HardwareBaseline.resolve("00048", pristine))
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
