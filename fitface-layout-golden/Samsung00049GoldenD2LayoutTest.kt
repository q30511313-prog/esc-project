package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD2LayoutTest {
    @Test
    fun compilesInjectedD2CleanPlateAndLiveGeometryWithoutTouchingSiblingStyles() {
        val source = real00049()
        val siblings = siblingBytes(source)
        val beforeImageCount = FaceRecordParser.scanImages(source.entryByBasename("style0.bin")).size

        val edit = GoldenD2LayoutCompiler.compile(
            source = source,
            cleanPlateArgb = deterministicCleanPlate(),
        )
        val output = edit.container
        val records = FaceRecordParser.scanWidgets(output.entryByBasename("style0.bin"))

        assertD2Geometry(records)
        assertEquals(beforeImageCount, FaceRecordParser.scanImages(output.entryByBasename("style0.bin")).size)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, output.entryByBasename(name).data)
        }
        assertTrue(output.fileSize < 4 * 1024 * 1024)
        assertTrue(output.validate().isValid)
        assertTrue(edit.changedPayloadBytes > 0)
    }

    @Test
    fun compilesApprovedEmbeddedD2CleanPlateWithoutCallerInjectedPixels() {
        val source = real00049()
        val siblings = siblingBytes(source)
        val beforeStyle0 = source.entryByBasename("style0.bin").data.copyOf()
        val beforeImageCount = FaceRecordParser.scanImages(source.entryByBasename("style0.bin")).size

        val edit = GoldenD2LayoutCompiler.compile(source)
        val output = edit.container
        val records = FaceRecordParser.scanWidgets(output.entryByBasename("style0.bin"))

        assertD2Geometry(records)
        assertEquals(
            "3718133cdd95f45155706222f5d402623aa62d0fe941b33d320090f26aa72b64",
            GoldenD2CleanPlate.RAW_RGB565_SHA256,
        )
        assertEquals(205824, GoldenD2CleanPlate.RAW_RGB565_BYTES)
        assertEquals(256 * 402, GoldenD2CleanPlate.argb().size)
        assertTrue(!beforeStyle0.contentEquals(output.entryByBasename("style0.bin").data))
        assertEquals(beforeImageCount, FaceRecordParser.scanImages(output.entryByBasename("style0.bin")).size)
        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, output.entryByBasename(name).data)
        }
        assertTrue(output.fileSize < 4 * 1024 * 1024)
        assertTrue(output.validate().isValid)
    }

    @Test
    fun rejectsWrongD2CleanPlateDimensionsBeforeMutation() {
        val source = real00049()
        try {
            GoldenD2LayoutCompiler.compile(source, intArrayOf(0xFF000000.toInt()))
            throw AssertionError("expected D2 clean-plate dimension rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("clean plate"))
        }
    }

    private fun assertD2Geometry(records: List<WidgetRecord>) {
        assertAt(records, 1, WIDGET_COMP, 0, 69, 48)
        assertAt(records, 2, WIDGET_PAIR, 17, 102, 75)
        assertAt(records, 3, WIDGET_SPRITE, 2, 64, 126)
        assertAt(records, 4, WIDGET_SPRITE, 3, 95, 126)
        assertAt(records, 5, WIDGET_SPRITE, 10, 133, 126)
        assertAt(records, 6, WIDGET_SPRITE, 11, 171, 126)
        assertAt(records, 7, WIDGET_SPRITE, 69, 175, 282)
        assertAt(records, 8, WIDGET_COMP, 0, 172, 312)
        assertAt(records, 9, WIDGET_PAIR, 5, 48, 105)
        assertAt(records, 11, WIDGET_COMP, 0, 58, 320)
        assertAt(records, 15, WIDGET_PAIR, 14, 108, 225)
        assertAt(records, 16, WIDGET_PAIR, 15, 132, 225)
        assertAt(records, 17, WIDGET_PAIR, 69, 164, 333)
    }

    private fun assertAt(
        records: List<WidgetRecord>,
        globalIndex: Int,
        type: Int,
        sequence: Int,
        x: Int,
        y: Int,
    ) {
        val record = records.single {
            it.globalIndex == globalIndex && it.widgetType == type && it.sequenceId == sequence
        }
        assertEquals(x, record.x)
        assertEquals(y, record.y)
    }

    private fun deterministicCleanPlate(): IntArray = IntArray(256 * 402) { index ->
        val x = index % 256
        val y = index / 256
        val red = (x * 5 + y) and 0x3F
        val green = (x + y * 3) and 0x3F
        val blue = (x * 2 + y * 5) and 0x3F
        (0xFF shl 24) or (red shl 16) or (green shl 8) or blue
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
