package dev.fitface.studio.core.format

import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Emits and reparses the final two-slot D3 package: D1 hardware style0 + D2 style1. */
class Samsung00049GoldenD3ArtifactTest {
    @Test
    fun emitsFinalCombinedContainerWithD1Style0AndD2Style1() {
        val outputDir = System.getenv("GOLDEN_D3_ARTIFACT_DIR")
            ?.takeIf { it.isNotBlank() }
            ?: throw AssertionError("GOLDEN_D3_ARTIFACT_DIR must be set by the D3 workflow")
        val pristine = real00049()
        val logical = GoldenD3Compiler.compile(pristine).container
        val expectedD1 = GoldenHardwareBaseline.resolve("00049", pristine)
            .entryByBasename("style0.bin").data
        val expectedD2 = logical.entryByBasename("style1.bin").data.copyOf()
        val style2 = pristine.entryByBasename("style2.bin").data.copyOf()
        val style3 = pristine.entryByBasename("style3.bin").data.copyOf()

        val compiled = GoldenD3HardwareBaseline.resolve("00049", pristine)
        assertTrue(compiled.validate().isValid)
        assertTrue(compiled.fileSize < 4 * 1024 * 1024)
        assertArrayEquals(expectedD1, compiled.entryByBasename("style0.bin").data)
        assertArrayEquals(expectedD2, compiled.entryByBasename("style1.bin").data)
        assertArrayEquals(style2, compiled.entryByBasename("style2.bin").data)
        assertArrayEquals(style3, compiled.entryByBasename("style3.bin").data)

        val style1Entry = compiled.entryByBasename("style1.bin")
        assertEquals(
            FaceRecordParser.scanImages(pristine.entryByBasename("style1.bin")).size,
            FaceRecordParser.scanImages(style1Entry).size,
        )
        assertEquals(GoldenD2CleanPlate.RAW_RGB565_SHA256, backgroundRgb565Sha256(style1Entry))

        val weather = FaceRecordParser.scanWidgets(style1Entry).single {
            it.globalIndex == 7 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 69
        }
        assertEquals(24, weather.words.size)
        assertEquals(175, weather.x)
        assertEquals(282, weather.y)

        val records = FaceRecordParser.scanWidgets(style1Entry)
        listOf(
            intArrayOf(1, WIDGET_COMP, 0, 69, 48),
            intArrayOf(2, WIDGET_PAIR, 17, 102, 75),
            intArrayOf(3, WIDGET_SPRITE, 2, 64, 126),
            intArrayOf(4, WIDGET_SPRITE, 3, 95, 126),
            intArrayOf(5, WIDGET_SPRITE, 10, 133, 126),
            intArrayOf(6, WIDGET_SPRITE, 11, 171, 126),
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
            assertEquals("style1 g${expected[0]} x", expected[3], record.x)
            assertEquals("style1 g${expected[0]} y", expected[4], record.y)
        }

        val directory = Path.of(outputDir)
        Files.createDirectories(directory)
        val output = directory.resolve("Golden-D3-style01-container.bin")
        Files.write(output, compiled.toByteArray())

        val reparsed = Fit3Container.parse(Files.readAllBytes(output))
        assertTrue(reparsed.validate().isValid)
        assertArrayEquals(compiled.toByteArray(), reparsed.toByteArray())
        assertEquals(compiled.fileSize.toLong(), Files.size(output))
    }

    private fun backgroundRgb565Sha256(entry: ContainerEntry): String {
        val image = FaceRecordParser.backgroundImage(entry)
            ?: throw AssertionError("style1 D2 background missing")
        assertEquals(IMAGE_RGB565, image.format)
        val bytes = entry.data.copyOfRange(
            image.samplesOffset,
            image.samplesOffset + image.width * image.height * image.bytesPerPixel,
        )
        return MessageDigest.getInstance("SHA-256")
            .digest(bytes)
            .joinToString("") { "%02x".format(it) }
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
