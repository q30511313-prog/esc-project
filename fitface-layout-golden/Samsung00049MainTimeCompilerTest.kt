package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049MainTimeCompilerTest {
    @Test
    fun resizesOneSharedDigitPoolAndPlacesAllFourMainTimeSprites() {
        val pristine = real00049()
        val staged = stageGoldenPrerequisites(pristine)
        val siblingStyles = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { staged.entryByBasename(it).data.copyOf() }
        val beforeImageCount = FaceRecordParser.scanImages(staged.entryByBasename("style0.bin")).size

        val edit = GoldenSemanticCompiler.compileMainTime(
            source = staged,
            pristine = pristine,
            entryBasename = "style0.bin",
            digitWidth = 27,
            digitHeight = 67,
            hourTensX = 77,
            hourOnesX = 106,
            minuteTensX = 142,
            minuteOnesX = 171,
            y = 139,
        )

        val style = edit.container.entryByBasename("style0.bin")
        val records = FaceRecordParser.scanWidgets(style)
        fun time(sequence: Int, globalIndex: Int, x: Int): WidgetRecord = records.single {
            it.widgetType == WIDGET_SPRITE &&
                it.sequenceId == sequence &&
                it.globalIndex == globalIndex &&
                it.x == x &&
                it.y == 139
        }
        val four = listOf(
            time(2, 3, 77),
            time(3, 4, 106),
            time(10, 5, 142),
            time(11, 6, 171),
        )

        val images = FaceRecordParser.scanImages(style)
        val firstImageOffset = images.first().recordOffset
        val byRelative = images.associateBy { (it.recordOffset - firstImageOffset).toLong() }
        val referenced = four.flatMap { record ->
            record.words.map { pointer ->
                requireNotNull(byRelative[pointer]) { "time pointer $pointer must resolve" }
            }
        }.distinctBy { it.index }

        assertEquals(10, referenced.size)
        referenced.forEach { image ->
            assertEquals(27, image.width)
            assertEquals(67, image.height)
            // Samsung 00049 ships this digit pool as opaque RGB565 (0x82), not
            // RGB565+A. The Golden resize must preserve the shipped raster format.
            assertEquals(IMAGE_RGB565, image.format)
            assertEquals(0, image.reserved)
            assertEquals(4, image.opaqueTrailerSize)
        }
        assertEquals(beforeImageCount, images.size)

        // Weather remains a separate untouched semantic pool after pointer relocation.
        val weather = records.single {
            it.globalIndex == 7 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 69
        }
        assertEquals(24, weather.words.size)
        val weatherImages = weather.words.map { pointer -> requireNotNull(byRelative[pointer]) }
        assertTrue(weatherImages.all { it.width == 30 && it.height == 30 })

        siblingStyles.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edit.container.entryByBasename(name).data)
        }
        assertTrue(edit.container.validate().isValid)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        assertTrue(edit.changedPayloadBytes > 0)
    }

    @Test
    fun failsClosedWhenMainTimeSpriteIdentityIsNotPristine() {
        val pristine = real00049()
        val staged = stageGoldenPrerequisites(pristine)
        val moved = FaceEditor.moveWidget(
            source = staged,
            entryBasename = "style0.bin",
            globalIndex = 3,
            widgetType = WIDGET_SPRITE,
            sequenceId = 2,
            x = 40,
            y = 100,
        ).container

        try {
            GoldenSemanticCompiler.compileMainTime(
                source = moved,
                pristine = pristine,
                entryBasename = "style0.bin",
                digitWidth = 27,
                digitHeight = 67,
                hourTensX = 77,
                hourOnesX = 106,
                minuteTensX = 142,
                minuteOnesX = 171,
                y = 139,
            )
            throw AssertionError("expected fail-closed time identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden main time"))
        }
    }

    private fun stageGoldenPrerequisites(source: Fit3Container): Fit3Container {
        var current = GoldenSemanticCompiler.compileSeconds(
            source = source,
            entryBasename = "style0.bin",
            tensX = 48,
            onesX = 72,
            y = 257,
        ).container
        current = GoldenSemanticCompiler.compileAmPm(
            source = current,
            entryBasename = "style0.bin",
            x = 48,
            y = 120,
        ).container
        current = GoldenDateCompiler.compile(
            source = current,
            entryBasename = "style0.bin",
            targetX = 65,
            targetY = 47,
        ).edit.container
        current = GoldenSemanticCompiler.compileWeekday(
            source = current,
            entryBasename = "style0.bin",
            x = 107,
            y = 80,
        ).container
        current = GoldenWeatherTextEditor.wire00049(
            source = current,
            entryBasename = "style0.bin",
            x = 112,
            y = 301,
        ).container
        current = GoldenSemanticCompiler.compileTempBattery(
            source = current,
            entryBasename = "style0.bin",
            tempX = 171,
            tempY = 260,
            batteryPercentX = 82,
            batteryPercentY = 336,
        ).container
        return current
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
