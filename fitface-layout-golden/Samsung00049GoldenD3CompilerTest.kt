package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** D3 expansion contract: keep approved D1 in style0 and install approved D2 in style1. */
class Samsung00049GoldenD3CompilerTest {
    @Test
    fun combinesD1AndD2WithoutTouchingStyle2OrStyle3() {
        val pristine = real00049()
        val untouched = listOf("style2.bin", "style3.bin")
            .associateWith { pristine.entryByBasename(it).data.copyOf() }
        val expectedD1 = GoldenD1LayoutCompiler.compile(pristine)
            .container.entryByBasename("style0.bin").data.copyOf()

        val compiled = GoldenD3Compiler.compile(pristine).container
        assertTrue(compiled.validate().isValid)
        assertTrue(compiled.fileSize < 4 * 1024 * 1024)
        assertArrayEquals(expectedD1, compiled.entryByBasename("style0.bin").data)

        val records = FaceRecordParser.scanWidgets(compiled.entryByBasename("style1.bin"))
        listOf(
            intArrayOf(1, WIDGET_COMP, 0, 69, 48),
            intArrayOf(2, WIDGET_PAIR, 17, 102, 75),
            intArrayOf(3, WIDGET_SPRITE, 2, 64, 126),
            intArrayOf(4, WIDGET_SPRITE, 3, 95, 126),
            intArrayOf(5, WIDGET_SPRITE, 10, 133, 126),
            intArrayOf(6, WIDGET_SPRITE, 11, 171, 126),
            intArrayOf(7, WIDGET_SPRITE, 69, 175, 282),
            intArrayOf(8, WIDGET_COMP, 0, 172, 312),
            intArrayOf(9, WIDGET_PAIR, 5, 48, 105),
            intArrayOf(11, WIDGET_COMP, 0, 58, 320),
            intArrayOf(15, WIDGET_PAIR, 14, 108, 225),
            intArrayOf(16, WIDGET_PAIR, 15, 132, 225),
            intArrayOf(17, WIDGET_PAIR, 69, 164, 333),
        ).forEach { expected ->
            val record = records.single {
                it.globalIndex == expected[0] &&
                    it.widgetType == expected[1] &&
                    it.sequenceId == expected[2]
            }
            assertEquals("g${expected[0]} x", expected[3], record.x)
            assertEquals("g${expected[0]} y", expected[4], record.y)
        }

        untouched.forEach { (name, bytes) ->
            assertArrayEquals(bytes, compiled.entryByBasename(name).data)
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
