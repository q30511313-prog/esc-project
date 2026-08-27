package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049WeatherTextCompilerTest {
    private val expectedLabels = listOf(
        "맑음", "구름조금", "흐림", "안개",
        "비", "비", "비", "소나기",
        "뇌우", "뇌우", "눈", "눈",
        "진눈깨비", "눈", "눈", "진눈깨비",
        "눈", "더움", "추움", "바람",
        "뇌우", "비", "바람", "회오리",
    )

    @Test
    fun weatherTextUsesTheSameSeq69WithoutTouchingAnyWeatherRaster() {
        val staged = stageGoldenPrerequisites(real00049())
        val beforeStyle = staged.entryByBasename("style0.bin").data
        val beforeImageOffset = beforeStyle.u32(0x14).toInt()
        val beforeImageSection = beforeStyle.copyOfRange(beforeImageOffset, beforeStyle.size)
        val beforeImages = FaceRecordParser.scanImages(staged.entryByBasename("style0.bin"))
        val untouchedStyles = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { staged.entryByBasename(it).data.copyOf() }

        val edit = GoldenWeatherTextEditor.wire00049(
            source = staged,
            entryBasename = "style0.bin",
            x = 112,
            y = 301,
        )

        val output = edit.container
        val records = FaceRecordParser.scanWidgets(output.entryByBasename("style0.bin"))
        val weatherSprite = records.single {
            it.globalIndex == 7 && it.widgetType == WIDGET_SPRITE && it.sequenceId == 69
        }
        val weatherText = records.single {
            it.globalIndex == 17 && it.widgetType == WIDGET_PAIR && it.sequenceId == 69
        }
        assertEquals(180, weatherSprite.x)
        assertEquals(102, weatherSprite.y)
        assertEquals(24, weatherSprite.words.size)

        assertEquals(112, weatherText.x)
        assertEquals(301, weatherText.y)
        assertEquals(2, weatherText.words[1].toInt() and 0xFF)
        assertEquals(0x0002000EL, weatherText.words[2])

        val groups = localeGroups(output.entryByBasename("font_ko.bin").data)
        assertEquals(38, groups.size)
        assertEquals(listOf("오전", "오후"), groups.subList(12, 14))
        assertEquals(expectedLabels, groups.subList(14, 38))
        assertEquals(expectedLabels, GoldenWeatherTextEditor.labelsKo)

        val afterStyle = output.entryByBasename("style0.bin").data
        val afterImageOffset = afterStyle.u32(0x14).toInt()
        val afterImageSection = afterStyle.copyOfRange(afterImageOffset, afterStyle.size)
        assertArrayEquals(beforeImageSection, afterImageSection)
        assertEquals(beforeImages.size, FaceRecordParser.scanImages(output.entryByBasename("style0.bin")).size)

        untouchedStyles.forEach { (name, bytes) ->
            assertArrayEquals(bytes, output.entryByBasename(name).data)
        }
        assertTrue(output.validate().isValid)
    }

    @Test
    fun weatherTextFailsClosedIfTheRemainingDonorIsNotPristine() {
        val staged = stageGoldenPrerequisites(real00049())
        val moved = FaceEditor.moveWidget(
            source = staged,
            entryBasename = "style0.bin",
            globalIndex = 17,
            widgetType = WIDGET_PAIR,
            sequenceId = 115,
            x = 170,
            y = 350,
        ).container

        try {
            GoldenWeatherTextEditor.wire00049(
                source = moved,
                entryBasename = "style0.bin",
                x = 112,
                y = 301,
            )
            throw AssertionError("expected fail-closed weather donor rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("Golden weather text donor"))
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
        return current
    }

    private fun localeGroups(data: ByteArray): List<String> {
        val count = data.u32(8).toInt()
        return (0 until count).map { index ->
            val descriptor = 0x18 + index * 8
            val length = data.u32(descriptor).toInt()
            val offset = data.u32(descriptor + 4).toInt()
            String(data, offset, length, StandardCharsets.UTF_8)
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
