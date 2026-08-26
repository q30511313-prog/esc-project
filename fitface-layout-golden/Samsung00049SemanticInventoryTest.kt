package dev.fitface.studio.core.format

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049SemanticInventoryTest {
    @Test
    fun style0HasExactGoldenSemanticSourcesAndDonors() {
        val stream = javaClass.getResourceAsStream(
            "/fixtures/SM-R390_00049_256x402.bin",
        )
        assertNotNull("real Samsung 00049 fixture must be staged by CI", stream)
        val source = Fit3Container.parse(requireNotNull(stream).readBytes())
        assertTrue(source.validate().isValid)

        val records = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin"))

        fun exact(
            type: Int,
            sequence: Int,
            globalIndex: Int,
            x: Int,
            y: Int,
        ): WidgetRecord = records.single {
            it.widgetType == type &&
                it.sequenceId == sequence &&
                it.globalIndex == globalIndex &&
                it.x == x &&
                it.y == y
        }

        exact(WIDGET_PAIR, 17, 2, 179, 36)      // weekday
        exact(WIDGET_SPRITE, 2, 3, 32, 93)     // hour tens
        exact(WIDGET_SPRITE, 3, 4, 86, 93)     // hour ones
        exact(WIDGET_SPRITE, 10, 5, 32, 174)   // minute tens
        exact(WIDGET_SPRITE, 11, 6, 88, 174)   // minute ones
        exact(WIDGET_SPRITE, 69, 7, 180, 102)  // weather state
        exact(WIDGET_BADGE, 37, 10, 34, 301)   // battery gauge

        val heartRateDonor = exact(WIDGET_PAIR, 41, 9, 172, 217)
        val stepsDonor = exact(WIDGET_PAIR, 29, 15, 23, 360)
        val kcalDonor = exact(WIDGET_PAIR, 48, 16, 101, 360)
        val activityDonor = exact(WIDGET_PAIR, 115, 17, 179, 360)

        assertEquals(1, heartRateDonor.words[1].toInt() and 0xFF)
        assertEquals(2, stepsDonor.words[1].toInt() and 0xFF)
        assertEquals(2, kcalDonor.words[1].toInt() and 0xFF)
        assertEquals(2, activityDonor.words[1].toInt() and 0xFF)

        val weather = records.single {
            it.widgetType == WIDGET_SPRITE && it.sequenceId == 69
        }
        assertEquals(24, weather.words.size)
    }
}
