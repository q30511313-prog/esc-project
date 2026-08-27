package dev.fitface.studio.core.format

import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD4InventoryTest {
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
        val bg = FaceRecordParser.backgroundImage(entry)
        println("D4_STYLE2_BG=${bg?.width}x${bg?.height}")
        assertTrue(d3.validate().isValid)
    }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also { assertTrue(it.validate().isValid) }
    }
}
