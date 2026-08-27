package dev.fitface.studio.core.format

import java.nio.file.Files
import java.nio.file.Path
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Emits the exact final Golden 00049 container while proving it can be reparsed. */
class Samsung00049GoldenArtifactTest {
    @Test
    fun emitsFinalGoldenContainerAfterLayoutAndOpticalLock() {
        val outputDir = System.getenv("GOLDEN_ARTIFACT_DIR")
            ?.takeIf { it.isNotBlank() }
            ?: throw AssertionError("GOLDEN_ARTIFACT_DIR must be set by the Task 8 workflow")
        val pristine = real00049()
        val siblings = siblingBytes(pristine)

        val compiled = GoldenHardwareBaseline.resolve(
            faceId = GoldenHardwareBaseline.TARGET_FACE_ID,
            stock = pristine,
        )
        assertTrue(compiled.validate().isValid)
        assertTrue(compiled.fileSize < 4 * 1024 * 1024)

        val records = FaceRecordParser.scanWidgets(compiled.entryByBasename("style0.bin"))
        listOf(1, 8, 11).forEach { globalIndex ->
            val composite = records.single {
                it.globalIndex == globalIndex && it.widgetType == WIDGET_COMP
            }
            assertEquals("Composite g$globalIndex", 0xFFB5B6BDL, composite.words[13])
        }
        listOf(17, 5, 14, 15, 69).forEach { sequence ->
            val pair = records.single {
                it.widgetType == WIDGET_PAIR && it.sequenceId == sequence
            }
            assertEquals("Pair seq $sequence", 0xFFB5B6BDL, pair.words[0])
        }
        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, compiled.entryByBasename(name).data)
        }

        val directory = Path.of(outputDir)
        Files.createDirectories(directory)
        val output = directory.resolve("Golden-style0-container.bin")
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
