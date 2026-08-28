package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * D5 = design04_8942 / 1000028942 on style3.
 *
 * The group anchors come from the frozen design04 recipe. HH:MM child origins are
 * the approved D4 optical 5:08 arrangement mapped from the design03 TIME box
 * (115 px wide) to design04 (107 px wide). The compact seconds group is 25 px wide,
 * so its two live Pair digits use 12 px origin spacing.
 */
class Samsung00049GoldenD5CompilerTest {
    @Test
    fun compilesApprovedDesign04IntoStyle3Only() {
        val pristine = real00049()
        val d4 = GoldenD4Compiler.compile(pristine).container
        val beforeStyle3 = d4.entryByBasename(STYLE3)
        val beforeImages = FaceRecordParser.scanImages(beforeStyle3).size

        val edit = GoldenD5Compiler.compile(pristine)
        val output = edit.container

        assertTrue(output.validate().isValid)
        assertTrue(output.fileSize < 4 * 1024 * 1024)
        assertTrue(edit.changedPayloadBytes > 0)
        assertEquals(listOf(STYLE3), edit.changedStyles)

        listOf("style0.bin", "style1.bin", "style2.bin").forEach { name ->
            assertArrayEquals(
                "D5 must preserve D4-approved sibling $name",
                d4.entryByBasename(name).data,
                output.entryByBasename(name).data,
            )
        }
        assertFalse(
            "D5 must change style3",
            beforeStyle3.data.contentEquals(output.entryByBasename(STYLE3).data),
        )

        val style3 = output.entryByBasename(STYLE3)
        assertEquals(beforeImages, FaceRecordParser.scanImages(style3).size)
        val bg = assertNotNull(FaceRecordParser.backgroundImage(style3))
        assertEquals(256, bg.width)
        assertEquals(402, bg.height)

        val records = FaceRecordParser.scanWidgets(style3)
        fun record(globalIndex: Int, type: Int, sequenceId: Int) = records.single {
            it.globalIndex == globalIndex &&
                it.widgetType == type &&
                it.sequenceId == sequenceId
        }
        fun assertAt(globalIndex: Int, type: Int, sequenceId: Int, x: Int, y: Int) {
            val r = record(globalIndex, type, sequenceId)
            assertEquals("g$globalIndex x", x, r.x)
            assertEquals("g$globalIndex y", y, r.y)
        }

        // design04 top strip: compact date / weekday / live battery.
        assertAt(1, WIDGET_COMP, 0, 55, 90)
        assertAt(2, WIDGET_PAIR, 17, 105, 76)
        assertAt(10, WIDGET_BADGE, 37, 173, 66)
        assertAt(11, WIDGET_COMP, 0, 175, 88)

        // Reuse the already-installed Korean AM/PM locale and remap donor Pair 41 -> 5.
        assertAt(9, WIDGET_PAIR, 5, 47, 127)

        // TIME box = 59,149 107x75. D4 optical child geometry scaled 115 -> 107.
        assertAt(3, WIDGET_SPRITE, 2, 55, 147)
        assertAt(4, WIDGET_SPRITE, 3, 82, 147)
        assertAt(5, WIDGET_SPRITE, 10, 111, 147)
        assertAt(6, WIDGET_SPRITE, 11, 141, 147)

        // SECONDS box = 181,180 25x29; remap donor Pair 29/48 -> live second 14/15.
        assertAt(15, WIDGET_PAIR, 14, 181, 180)
        assertAt(16, WIDGET_PAIR, 15, 193, 180)

        // Lower design04 weather strip.
        assertAt(7, WIDGET_SPRITE, 69, 59, 262)
        assertAt(17, WIDGET_PAIR, 69, 99, 272)
        assertAt(8, WIDGET_COMP, 0, 169, 272)
    }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also { assertTrue(it.validate().isValid) }
    }

    private companion object {
        const val STYLE3 = "style3.bin"
    }
}
