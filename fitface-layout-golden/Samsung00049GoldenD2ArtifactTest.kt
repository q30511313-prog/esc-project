package dev.fitface.studio.core.format

import java.nio.file.Files
import java.nio.file.Path
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Emits and reparses the exact approved D2 (1000028943) style0 container. */
class Samsung00049GoldenD2ArtifactTest {
    @Test
    fun emitsFinalD2ContainerWithApprovedCleanPlateAndGeometry() {
        val outputDir = System.getenv("GOLDEN_D2_ARTIFACT_DIR")
            ?.takeIf { it.isNotBlank() }
            ?: throw AssertionError("GOLDEN_D2_ARTIFACT_DIR must be set by the D2 workflow")
        val pristine = real00049()
        val siblings = siblingBytes(pristine)

        val compiled = GoldenD2LayoutCompiler.compile(pristine).container
        assertTrue(compiled.validate().isValid)
        assertTrue(compiled.fileSize < 4 * 1024 * 1024)
        assertEquals(
            "3718133cdd95f45155706222f5d402623aa62d0fe941b33d320090f26aa72b64",
            GoldenD2CleanPlate.RAW_RGB565_SHA256,
        )
        assertEquals(205824, GoldenD2CleanPlate.RAW_RGB565_BYTES)
        assertEquals(256 * 402, GoldenD2CleanPlate.argb().size)

        val records = FaceRecordParser.scanWidgets(compiled.entryByBasename("style0.bin"))
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

        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, compiled.entryByBasename(name).data)
        }

        val directory = Path.of(outputDir)
        Files.createDirectories(directory)
        val output = directory.resolve("Golden-D2-style0-container.bin")
        Files.write(output, compiled.toByteArray())

        val reparsed = Fit3Container.parse(Files.readAllBytes(output))
        assertTrue(reparsed.validate().isValid)
        assertArrayEquals(compiled.toByteArray(), reparsed.toByteArray())
        assertEquals(compiled.fileSize.toLong(), Files.size(output))
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
