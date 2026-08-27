package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenLayoutTest {
    @Test
    fun styleScopedBackgroundReplacementChangesOnlyStyle0() {
        val source = real00049()
        val beforeStyle0 = source.entryByBasename("style0.bin").data.copyOf()
        val siblingStyles = siblingBytes(source)
        val beforeImages = FaceRecordParser.scanImages(source.entryByBasename("style0.bin"))
        val beforeBackground = requireNotNull(FaceRecordParser.backgroundImage(source.entryByBasename("style0.bin")))

        val edit = FaceEditor.replaceBackgroundInStyle(
            source = source,
            entryBasename = "style0.bin",
            width = 256,
            height = 402,
            argb = deterministicCleanPlate(),
        )

        val afterStyle0 = edit.container.entryByBasename("style0.bin")
        val afterBackground = requireNotNull(FaceRecordParser.backgroundImage(afterStyle0))
        assertTrue(!beforeStyle0.contentEquals(afterStyle0.data))
        assertEquals(256, afterBackground.width)
        assertEquals(402, afterBackground.height)
        assertEquals(beforeBackground.format, afterBackground.format)
        assertEquals(beforeImages.size, FaceRecordParser.scanImages(afterStyle0).size)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        siblingStyles.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edit.container.entryByBasename(name).data)
        }
        assertTrue(edit.container.validate().isValid)
    }

    @Test
    fun compilesCleanPlateAndAllD1LiveGeometryAtomicallyWithoutTouchingSiblingStyles() {
        val source = real00049()
        val siblings = siblingBytes(source)
        val beforeImageCount = FaceRecordParser.scanImages(source.entryByBasename("style0.bin")).size

        val edit = GoldenD1LayoutCompiler.compile(
            source = source,
            cleanPlateArgb = deterministicCleanPlate(),
        )
        val output = edit.container
        val records = FaceRecordParser.scanWidgets(output.entryByBasename("style0.bin"))

        assertGoldenGeometry(records)

        val gauge = records.single { it.globalIndex == 10 && it.widgetType == WIDGET_BADGE && it.sequenceId == 37 }
        assertEquals(34, gauge.x)
        assertEquals(301, gauge.y)

        assertEquals(beforeImageCount, FaceRecordParser.scanImages(output.entryByBasename("style0.bin")).size)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, output.entryByBasename(name).data)
        }
        assertTrue(output.validate().isValid)
        assertTrue(edit.changedPayloadBytes > 0)
    }

    @Test
    fun compilesApprovedEmbeddedD1CleanPlateWithoutCallerInjectedPixels() {
        val source = real00049()
        val siblings = siblingBytes(source)
        val beforeImageCount = FaceRecordParser.scanImages(source.entryByBasename("style0.bin")).size

        val edit = GoldenD1LayoutCompiler.compile(source)
        val output = edit.container
        val records = FaceRecordParser.scanWidgets(output.entryByBasename("style0.bin"))

        assertGoldenGeometry(records)
        assertEquals(
            "e12a722dc7a1e51bde71c9ffa375e0ec9443521e9da9feaef77819ee8e939c3e",
            GoldenD1CleanPlate.RAW_RGB565_SHA256,
        )
        assertEquals(205824, GoldenD1CleanPlate.RAW_RGB565_BYTES)
        assertEquals(256 * 402, GoldenD1CleanPlate.argb().size)
        assertEquals(beforeImageCount, FaceRecordParser.scanImages(output.entryByBasename("style0.bin")).size)
        assertEquals(listOf("style0.bin"), edit.changedStyles.distinct())
        siblings.forEach { (name, bytes) ->
            assertArrayEquals(bytes, output.entryByBasename(name).data)
        }
        assertTrue(output.validate().isValid)
        assertTrue(edit.changedPayloadBytes > 0)
    }

    @Test
    fun appliesApprovedOpticalLockAfterLayoutWithoutTintingCleanPlateOrSiblingStyles() {
        val source = real00049()
        val layout = GoldenD1LayoutCompiler.compile(source).container
        val siblings = siblingBytes(layout)
        val layoutEntry = layout.entryByBasename("style0.bin")
        val beforeImageCount = FaceRecordParser.scanImages(layoutEntry).size
        val backgroundPoints = listOf(10 to 10, 128 to 220, 230 to 390)
            .associateWith { (x, y) -> backgroundRgb565(layout, x, y) }

        val edit = GoldenD1OpticalLock.compile(layout)
        val output = edit.container
        val records = FaceRecordParser.scanWidgets(output.entryByBasename("style0.bin"))

        assertEquals(0xB8B8AD, GoldenD1OpticalLock.LOGICAL_RGB888)
        assertEquals(0xB5B6BD, GoldenD1OpticalLock.OPTICAL_RGB888)
        assertEquals(0xB5B7, GoldenD1OpticalLock.OPTICAL_RGB565)

        listOf(17, 5, 14, 15, 69).forEach { sequence ->
            val pair = records.single {
                it.widgetType == WIDGET_PAIR && it.sequenceId == sequence
            }
            assertEquals("Pair seq $sequence", 0xFFB5B6BDL, pair.words[0])
        }

        // Cross-style stock evidence proves words[13] is the colour slot for these
        // exact 00049 Composites. g8 is the special case whose stock colour is opaque
        // white (0xFFFFFFFF) in all four styles; Golden must still lock it optically.
        listOf(1, 8, 11).forEach { globalIndex ->
            val composite = records.single {
                it.globalIndex == globalIndex && it.widgetType == WIDGET_COMP
            }
            assertEquals("Composite g$globalIndex", 0xFFB5B6BDL, composite.words[13])
        }

        assertEquals(0xB5B7, firstVisibleSpriteRgb565(output, globalIndex = 4, sequenceId = 3))
        assertEquals(0xB5B7, firstVisibleSpriteRgb565(output, globalIndex = 7, sequenceId = 69))

        backgroundPoints.forEach { (point, before) ->
            assertEquals("clean plate pixel $point", before, backgroundRgb565(output, point.first, point.second))
        }
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
    fun rejectsWrongCleanPlateDimensionsBeforeAnyMutation() {
        val source = real00049()
        try {
            GoldenD1LayoutCompiler.compile(source, intArrayOf(0xFF000000.toInt()))
            throw AssertionError("expected clean-plate dimension rejection")
        } catch (error: Fit3FormatException) {
            assertTrue(error.message.orEmpty().contains("clean plate"))
        }
    }

    private fun assertGoldenGeometry(records: List<WidgetRecord>) {
        assertAt(records, 1, WIDGET_COMP, 0, 65, 47)
        assertAt(records, 2, WIDGET_PAIR, 17, 107, 80)
        assertAt(records, 3, WIDGET_SPRITE, 2, 77, 139)
        assertAt(records, 4, WIDGET_SPRITE, 3, 106, 139)
        assertAt(records, 5, WIDGET_SPRITE, 10, 142, 139)
        assertAt(records, 6, WIDGET_SPRITE, 11, 171, 139)
        assertAt(records, 7, WIDGET_SPRITE, 69, 113, 261)
        assertAt(records, 8, WIDGET_COMP, 0, 171, 260)
        assertAt(records, 9, WIDGET_PAIR, 5, 48, 120)
        assertAt(records, 11, WIDGET_COMP, 0, 82, 336)
        assertAt(records, 15, WIDGET_PAIR, 14, 48, 257)
        assertAt(records, 16, WIDGET_PAIR, 15, 72, 257)
        assertAt(records, 17, WIDGET_PAIR, 69, 112, 301)
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

    private fun firstVisibleSpriteRgb565(
        container: Fit3Container,
        globalIndex: Int,
        sequenceId: Int,
    ): Int {
        val entry = container.entryByBasename("style0.bin")
        val record = FaceRecordParser.scanWidgets(entry).single {
            it.globalIndex == globalIndex &&
                it.widgetType == WIDGET_SPRITE &&
                it.sequenceId == sequenceId
        }
        val images = FaceRecordParser.scanImages(entry)
        val firstImageOffset = images.first().recordOffset
        val image = images.single {
            (it.recordOffset - firstImageOffset).toLong() == record.words.first()
        }
        val bytes = container.toByteArray()
        repeat(image.width * image.height) { pixel ->
            val absolute = entry.offset + image.samplesOffset + pixel * image.bytesPerPixel
            val visible = image.bytesPerPixel < 3 || (bytes[absolute + 2].toInt() and 0xFF) != 0
            if (visible) return bytes.u16(absolute)
        }
        throw AssertionError("Sprite g$globalIndex/seq$sequenceId has no visible pixels")
    }

    private fun backgroundRgb565(container: Fit3Container, x: Int, y: Int): Int {
        val entry = container.entryByBasename("style0.bin")
        val background = requireNotNull(FaceRecordParser.backgroundImage(entry))
        val absolute = entry.offset + background.samplesOffset +
            (y * background.width + x) * background.bytesPerPixel
        return container.toByteArray().u16(absolute)
    }

    private fun deterministicCleanPlate(): IntArray = IntArray(256 * 402) { index ->
        val x = index % 256
        val y = index / 256
        val red = (x * 3 + y) and 0x3F
        val green = (x + y * 2) and 0x3F
        val blue = (x * 2 + y * 3) and 0x3F
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
