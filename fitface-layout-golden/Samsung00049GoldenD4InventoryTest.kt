package dev.fitface.studio.core.format

import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD4InventoryTest {
    private data class Target(val globalIndex: Int, val x: Int, val y: Int)

    private val targets = listOf(
        Target(0, 74, 61),
        Target(1, 132, 61),
        Target(2, 160, 61),
        Target(10, 103, 88),
        Target(8, 58, 113),
        Target(3, 77, 128),
        Target(4, 106, 128),
        Target(5, 137, 128),
        Target(6, 169, 128),
        Target(7, 103, 218),
        Target(13, 97, 286),
        Target(11, 163, 283),
        Target(12, 137, 322),
    )

    @Test
    fun printsStyle2InventoryAfterApprovedD3Baseline() {
        val pristine = real00049()
        val d3 = GoldenD3Compiler.compile(pristine).container
        val entry = d3.entryByBasename("style2.bin")
        val records = FaceRecordParser.scanWidgets(entry)
        println("D4_STYLE2_WIDGET_COUNT=${records.size}")
        records.forEach {
            println(
                "D4_STYLE2 g=${it.globalIndex} type=${it.widgetType} seq=${it.sequenceId} " +
                    "x=${it.x} y=${it.y} words=${it.words.joinToString(",")}",
            )
        }
        printSeq5("initial", records)
        val bg = FaceRecordParser.backgroundImage(entry)
        println("D4_STYLE2_BG=${bg?.width}x${bg?.height}")
        assertTrue(d3.validate().isValid)
    }

    @Test
    fun tracesSeq5AcrossApprovedD4TargetMoves() {
        val pristine = real00049()
        var current = GoldenD3Compiler.compile(pristine).container
        val initial = FaceRecordParser.scanWidgets(current.entryByBasename("style2.bin"))
            .filter { it.sequenceId == 5 }
        var firstCountChange = "none"
        printSeq5("initial", FaceRecordParser.scanWidgets(current.entryByBasename("style2.bin")))

        targets.forEach { target ->
            val records = FaceRecordParser.scanWidgets(current.entryByBasename("style2.bin"))
            val record = records.single { it.globalIndex == target.globalIndex }
            if (record.x != target.x || record.y != target.y) {
                current = FaceEditor.moveWidget(
                    source = current,
                    entryBasename = "style2.bin",
                    globalIndex = record.globalIndex,
                    widgetType = record.widgetType,
                    sequenceId = record.sequenceId,
                    x = target.x,
                    y = target.y,
                ).container
            }
            val after = FaceRecordParser.scanWidgets(current.entryByBasename("style2.bin"))
            val seq5 = after.filter { it.sequenceId == 5 }
            if (firstCountChange == "none" && seq5.size != initial.size) {
                firstCountChange = "g${target.globalIndex}"
            }
            printSeq5("after_g${target.globalIndex}", after)
        }

        val finalSeq5 = FaceRecordParser.scanWidgets(current.entryByBasename("style2.bin"))
            .filter { it.sequenceId == 5 }
        val initialIds = compact(initial)
        val finalIds = compact(finalSeq5)
        println(
            "D4_SEQ5_DIAG initial=${initial.size}:$initialIds final=${finalSeq5.size}:$finalIds " +
                "firstCountChange=$firstCountChange",
        )
        assertTrue(current.validate().isValid)
    }

    private fun printSeq5(stage: String, records: List<FaceWidgetRecord>) {
        val candidates = records.filter { it.sequenceId == 5 }
        println("D4_SEQ5 stage=$stage count=${candidates.size} candidates=${compact(candidates)}")
    }

    private fun compact(records: List<FaceWidgetRecord>): String = records.joinToString(";") {
        "g${it.globalIndex}/t${it.widgetType}/x${it.x}/y${it.y}"
    }.ifEmpty { "none" }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also { assertTrue(it.validate().isValid) }
    }
}
