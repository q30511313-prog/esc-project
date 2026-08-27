package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD3HardwareBaselineTest {
    @Test
    fun locksD1HardwareStyle0WhilePreservingD2Style1AndUntouchedSiblings() {
        val pristine = real00049()
        val logical = GoldenD3Compiler.compile(pristine).container
        val expectedD1Hardware = GoldenHardwareBaseline.resolve("00049", pristine)
            .entryByBasename("style0.bin").data
        val expectedD2 = logical.entryByBasename("style1.bin").data.copyOf()
        val style2 = pristine.entryByBasename("style2.bin").data.copyOf()
        val style3 = pristine.entryByBasename("style3.bin").data.copyOf()

        val resolved = GoldenD3HardwareBaseline.resolve("00049", pristine)
        assertTrue(resolved.validate().isValid)
        assertTrue(resolved.fileSize < 4 * 1024 * 1024)
        assertArrayEquals(expectedD1Hardware, resolved.entryByBasename("style0.bin").data)
        assertArrayEquals(expectedD2, resolved.entryByBasename("style1.bin").data)
        assertArrayEquals(style2, resolved.entryByBasename("style2.bin").data)
        assertArrayEquals(style3, resolved.entryByBasename("style3.bin").data)
    }

    @Test
    fun leavesNonTargetFaceByIdentity() {
        val pristine = real00049()
        assertSame(pristine, GoldenD3HardwareBaseline.resolve("00048", pristine))
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
