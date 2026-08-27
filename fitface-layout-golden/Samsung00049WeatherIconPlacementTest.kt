package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049WeatherIconPlacementTest {
    @Test
    fun movesWeatherSpriteIntoD1BoxWithoutRewritingAnyWeatherFrame() {
        val pristine = real00049()
        val staged = stageGolden(pristine)
        val styleBefore = staged.entryByBasename("style0.bin")
        val recordsBefore = FaceRecordParser.scanWidgets(styleBefore)
        val weatherBefore = recordsBefore.single {
            it.globalIndex == 7 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 69
        }
        assertEquals(180, weatherBefore.x)
        assertEquals(102, weatherBefore.y)
        assertEquals(24, weatherBefore.words.size)

        val imagesBefore = FaceRecordParser.scanImages(styleBefore)
        val firstBefore = imagesBefore.first().recordOffset
        val byRelativeBefore = imagesBefore.associateBy { (it.recordOffset - firstBefore).toLong() }
        val weatherFrameBytes = weatherBefore.words.associateWith { pointer ->
            val image = requireNotNull(byRelativeBefore[pointer])
            val end = image.pixelOffset + image.dataSize
            styleBefore.data.copyOfRange(image.recordOffset, end)
        }
        val imageCountBefore = imagesBefore.size
        val siblings = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { staged.entryByBasename(it).data.copyOf() }

        val edit = GoldenSemanticCompiler.compileWeatherIcon(
            source = staged,
            entryBasename = "style0.bin",
            x = 113,
            y = 261,
        )

        val styleAfter = edit.container.entryByBasename("style0.bin")
        val recordsAfter = FaceRecordParser.scanWidgets(styleAfter)
        val weatherAfter = recordsAfter.single {
            it.globalIndex == 7 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 69
        }
        assertEquals(113, weatherAfter.x)
        assertEquals(261, weatherAfter.y)
        assertEquals(weatherBefore.words, weatherAfter.words)

        val imagesAfter = FaceRecordParser.scanImages(styleAfter)
        assertEquals(imageCountBefore, imagesAfter.size)
        val firstAfter = imagesAfter.first().recordOffset
        val byRelativeAfter = imagesAfter.associateBy { (it.recordOffset - firstAfter).toLong() }
        weatherAfter.words.forEach { pointer ->
            val image = requireNotNull(byRelativeAfter[pointer])
            assertEquals(30, image.width)
            assertEquals(30, image.height)
            assertEquals(IMAGE_RGB565_ALPHA, image.format)
            val end = image.pixelOffset + image.dataSize
            assertArrayEquals(
                weatherFrameBytes.getValue(pointer),
                styleAfter.data.copyOfRange(image.recordOffset, end),
            )
        }

        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edit.container.entryByBasename(name).data)
        }
        assertTrue(edit.container.validate().isValid)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
    }

    @Test
    fun failsClosedWhenWeatherSpriteIdentityIsNotPristine() {
        val pristine = real00049()
        val staged = stageGolden(pristine)
        val moved = FaceEditor.moveWidget(
            source = staged,
            entryBasename = "style0.bin",
            globalIndex = 7,
            widgetType = WIDGET_SPRITE,
            sequenceId = 69,
            x = 181,
            y = 102,
        ).container

        try {
            GoldenSemanticCompiler.compileWeatherIcon(
                source = moved,
                entryBasename = "style0.bin",
                x = 113,
                y = 261,
            )
            throw AssertionError("expected fail-closed weather identity rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden weather icon"))
        }
    }

    private fun stageGolden(pristine: Fit3Container): Fit3Container {
        var current = GoldenSemanticCompiler.compileSeconds(
            source = pristine,
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
        current = GoldenSemanticCompiler.compileMainTime(
            source = current,
            pristine = pristine,
            entryBasename = "style0.bin",
            digitWidth = 27,
            digitHeight = 67,
            hourTensX = 77,
            hourOnesX = 106,
            minuteTensX = 142,
            minuteOnesX = 171,
            y = 139,
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
