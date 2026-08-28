package dev.fitface.studio.core.format

import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * D5 baseline probe. D4 is compiled first, then stock style3 is inventoried without
 * mutation so the D5 contract can be based on the real Samsung 00049 record layout.
 */
class Samsung00049GoldenD5InventoryTest {
    @Test
    fun printsStyle3InventoryAfterApprovedD4Baseline() {
        val pristine = real00049()
        val d4 = GoldenD4Compiler.compile(pristine).container
        val entry = d4.entryByBasename("style3.bin")
        val records = FaceRecordParser.scanWidgets(entry)
        val images = FaceRecordParser.scanImages(entry)
        val bg = FaceRecordParser.backgroundImage(entry)

        println("D5_STYLE3_WIDGET_COUNT=${records.size}")
        println("D5_STYLE3_IMAGE_COUNT=${images.size}")
        println("D5_STYLE3_BG=${bg?.width}x${bg?.height} format=${bg?.format}")
        records.forEach {
            println(
                "D5_STYLE3 g=${it.globalIndex} type=${it.widgetType} seq=${it.sequenceId} " +
                    "x=${it.x} y=${it.y} w=${it.width} h=${it.height} " +
                    "words=${it.words.joinToString(",")}",
            )
        }
        val byType = records.groupingBy { it.widgetType }.eachCount().toSortedMap()
        val bySeq = records.groupingBy { it.sequenceId }.eachCount().toSortedMap()
        println("D5_STYLE3_TYPES=" + byType.entries.joinToString(",") { "${it.key}:${it.value}" })
        println("D5_STYLE3_SEQS=" + bySeq.entries.joinToString(",") { "${it.key}:${it.value}" })

        assertTrue(d4.validate().isValid)
        assertTrue(d4.fileSize < 4 * 1024 * 1024)
    }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also { assertTrue(it.validate().isValid) }
    }
}
