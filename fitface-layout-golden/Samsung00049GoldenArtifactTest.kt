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
        assertGoldenGeometry(records)
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
        assertEquals(0xB5B7, firstVisibleSpriteRgb565(compiled, globalIndex = 4, sequenceId = 3))
        assertEquals(0xB5B7, firstVisibleSpriteRgb565(compiled, globalIndex = 7, sequenceId = 69))
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

    private fun assertGoldenGeometry(records: List<WidgetRecord>) {
        listOf(
            intArrayOf(1, WIDGET_COMP, 0, 65, 47),
            intArrayOf(2, WIDGET_PAIR, 17, 107, 80),
            intArrayOf(3, WIDGET_SPRITE, 2, 77, 139),
            intArrayOf(4, WIDGET_SPRITE, 3, 106, 139),
            intArrayOf(5, WIDGET_SPRITE, 10, 142, 139),
            intArrayOf(6, WIDGET_SPRITE, 11, 171, 139),
            intArrayOf(7, WIDGET_SPRITE, 69, 113, 261),
            intArrayOf(8, WIDGET_COMP, 0, 171, 260),
            intArrayOf(9, WIDGET_PAIR, 5, 48, 120),
            intArrayOf(11, WIDGET_COMP, 0, 82, 336),
            intArrayOf(15, WIDGET_PAIR, 14, 48, 257),
            intArrayOf(16, WIDGET_PAIR, 15, 72, 257),
            intArrayOf(17, WIDGET_PAIR, 69, 112, 301),
        ).forEach { identity ->
            val record = records.single {
                it.globalIndex == identity[0] &&
                    it.widgetType == identity[1] &&
                    it.sequenceId == identity[2]
            }
            assertEquals("g${identity[0]} x", identity[3], record.x)
            assertEquals("g${identity[0]} y", identity[4], record.y)
        }
    }

    private fun firstVisibleSpriteRgb565(
        container: Fit3Container,
        globalIndex: Int,
        sequenceId: Int,
    ): Int {
        val entry = container.entryByBasename("style0.bin")
        val record = FaceRecordParser.scanWidgets(entry).single {
            it.globalIndex == globalIndex &&
                it.widgetType == WIDGET_SPRITE &&
                it.sequenceId == sequenceId
        }
        val images = FaceRecordParser.scanImages(entry)
        val firstImageOffset = images.first().recordOffset
        val image = images.single {
            (it.recordOffset - firstImageOffset).toLong() == record.words.first()
        }
        val bytes = container.toByteArray()
        repeat(image.width * image.height) { pixel ->
            val absolute = entry.offset + image.samplesOffset + pixel * image.bytesPerPixel
            val visible = image.bytesPerPixel < 3 || (bytes[absolute + 2].toInt() and 0xFF) != 0
            if (visible) return bytes.u16(absolute)
        }
        throw AssertionError("Sprite g$globalIndex/seq$sequenceId has no visible pixels")
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
