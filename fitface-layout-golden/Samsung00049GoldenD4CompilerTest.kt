package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Locks D4 to style2 / approved 1000028941 artwork while preserving D1+D2 and stock style3. */
class Samsung00049GoldenD4CompilerTest {
    private companion object {
        const val D4_CLEAN_PLATE_SHA256 =
            "7fe888c2f4536801c916cbdcf026cbad1392a0cd54ff6ad82b00ca2093a34db8"
    }

    @Test
    fun compilesOnlyStyle2OnTopOfApprovedD3Baseline() {
        val pristine = real00049()
        val d3 = GoldenD3Compiler.compile(pristine).container
        val edit = GoldenD4Compiler.compile(pristine)
        val out = edit.container

        assertTrue(out.validate().isValid)
        assertTrue(out.fileSize < 4 * 1024 * 1024)
        assertEquals(listOf("style2.bin"), edit.changedStyles)
        assertTrue(edit.changedPayloadBytes > 0)

        assertArrayEquals(d3.entryByBasename("style0.bin").data, out.entryByBasename("style0.bin").data)
        assertArrayEquals(d3.entryByBasename("style1.bin").data, out.entryByBasename("style1.bin").data)
        assertFalse(d3.entryByBasename("style2.bin").data.contentEquals(out.entryByBasename("style2.bin").data))
        assertArrayEquals(pristine.entryByBasename("style3.bin").data, out.entryByBasename("style3.bin").data)

        val style2 = out.entryByBasename("style2.bin")
        val bg = FaceRecordParser.backgroundImage(style2)
            ?: throw AssertionError("D4 style2 background missing")
        assertEquals(256, bg.width)
        assertEquals(402, bg.height)
        assertEquals(IMAGE_RGB565, bg.format)
        assertEquals(256 * 402 * 2, bg.pixelDataSize)
        val backgroundBytes = style2.data.copyOfRange(
            bg.samplesOffset,
            bg.samplesOffset + bg.pixelDataSize,
        )
        assertEquals(D4_CLEAN_PLATE_SHA256, sha256(backgroundBytes))

        val records = FaceRecordParser.scanWidgets(style2)
        listOf(
            intArrayOf(0, 74, 61),
            intArrayOf(1, 132, 61),
            intArrayOf(2, 160, 61),
            intArrayOf(10, 103, 88),
            intArrayOf(8, 58, 113),
            intArrayOf(3, 77, 128),
            intArrayOf(4, 106, 128),
            intArrayOf(5, 137, 128),
            intArrayOf(6, 169, 128),
            intArrayOf(7, 103, 218),
            intArrayOf(13, 97, 286),
            intArrayOf(11, 163, 283),
            intArrayOf(12, 137, 322),
        ).forEach { expected ->
            val record = records.single { it.globalIndex == expected[0] }
            assertEquals("style2 g${expected[0]} x", expected[1], record.x)
            assertEquals("style2 g${expected[0]} y", expected[2], record.y)
        }
        val weather = records.single {
            it.globalIndex == 9 && it.widgetType == 5 && it.sequenceId == 41
        }
        assertEquals(60, weather.x)
        assertEquals(282, weather.y)
    }

    private fun sha256(bytes: ByteArray): String =
        java.security.MessageDigest.getInstance("SHA-256")
            .digest(bytes)
            .joinToString("") { "%02x".format(it) }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"))
        return Fit3Container.parse(stream.readBytes()).also { assertTrue(it.validate().isValid) }
    }
}
