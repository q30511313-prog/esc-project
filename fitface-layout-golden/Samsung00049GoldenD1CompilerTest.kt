package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.WATCH_CONTAINER_BYTE_CEILING
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD1CompilerTest {
    @Test
    fun compilesAllD1LiveSemanticsAtomicallyFromPristine00049() {
        val pristine = real00049()
        val originalImageCount = FaceRecordParser.scanImages(
            pristine.entryByBasename("style0.bin"),
        ).size
        val siblings = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { pristine.entryByBasename(it).data.copyOf() }

        val edit = GoldenD1Compiler.compile(pristine)
        val result = edit.container
        val style = result.entryByBasename("style0.bin")
        val records = FaceRecordParser.scanWidgets(style)

        fun record(type: Int, sequence: Int, x: Int, y: Int): WidgetRecord =
            records.single { it.widgetType == type && it.sequenceId == sequence && it.x == x && it.y == y }

        // D1 live layout targets.
        record(WIDGET_COMP, 0, 65, 47)       // native live month/day date fallback
        record(WIDGET_PAIR, 17, 107, 80)     // weekday
        record(WIDGET_PAIR, 5, 48, 120)      // 오전/오후
        record(WIDGET_SPRITE, 2, 77, 139)    // hour tens
        record(WIDGET_SPRITE, 3, 106, 139)   // hour ones
        record(WIDGET_SPRITE, 10, 142, 139)  // minute tens
        record(WIDGET_SPRITE, 11, 171, 139)  // minute ones
        record(WIDGET_PAIR, 14, 48, 257)     // second tens
        record(WIDGET_PAIR, 15, 72, 257)     // second ones
        record(WIDGET_SPRITE, 69, 113, 261)  // native weather icon
        record(WIDGET_PAIR, 69, 112, 301)    // synchronized Korean weather text

        val temperature = record(WIDGET_COMP, 0, 171, 260)
        assertEquals(0xFFFF003EL, temperature.words.first()) // inner source 62
        val battery = record(WIDGET_COMP, 0, 82, 336)
        assertEquals(0xFFFF0025L, battery.words.first()) // inner source 37

        val images = FaceRecordParser.scanImages(style)
        assertEquals(originalImageCount, images.size)

        // HH:MM is one resized opaque ten-frame pool.
        val imageStart = images.first().recordOffset
        val byRelative = images.associateBy { (it.recordOffset - imageStart).toLong() }
        val timeRecords = records.filter { it.widgetType == WIDGET_SPRITE && it.sequenceId in setOf(2, 3, 10, 11) }
        val timeImages = timeRecords.flatMap { it.words }.map { requireNotNull(byRelative[it]) }.distinctBy { it.index }
        assertEquals(10, timeImages.size)
        assertTrue(timeImages.all {
            it.width == 27 && it.height == 67 && it.format == IMAGE_RGB565 && it.opaqueTrailerSize == 4
        })

        // Weather raster pool stays native and image-count neutral.
        val weatherSprite = records.single { it.widgetType == WIDGET_SPRITE && it.sequenceId == 69 }
        val weatherImages = weatherSprite.words.map { requireNotNull(byRelative[it]) }
        assertEquals(24, weatherImages.distinctBy { it.index }.size)
        assertTrue(weatherImages.all {
            it.width == 30 && it.height == 30 && it.format == IMAGE_RGB565_ALPHA
        })

        val ko = result.entryByBasename("font_ko.bin").data
        assertEquals(38L, ko.u32(8)) // 12 stock + AM/PM 2 + weather text 24

        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, result.entryByBasename(name).data)
        }
        assertEquals(18, records.size) // semantic repurpose, not record fabrication
        assertTrue(result.fileSize <= WATCH_CONTAINER_BYTE_CEILING)
        assertTrue(result.validate().isValid)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        assertTrue(edit.changedPayloadBytes > 0)
    }

    @Test
    fun refusesToCompileAgainOverAnAlreadyCompiledGoldenD1() {
        val pristine = real00049()
        val compiled = GoldenD1Compiler.compile(pristine).container
        try {
            GoldenD1Compiler.compile(compiled)
            throw AssertionError("expected fail-closed repeated Golden D1 compile")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().isNotBlank())
        }
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
