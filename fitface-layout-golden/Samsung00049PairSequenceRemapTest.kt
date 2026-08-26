package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class Samsung00049PairSequenceRemapTest {
    @Test
    fun remapsExactlyOneStyle0PairAndLeavesSiblingStylesByteIdentical() {
        val source = real00049()
        val style0 = source.entryByBasename("style0.bin")
        val donor = FaceRecordParser.scanWidgets(style0).single {
            it.widgetType == WIDGET_PAIR &&
                it.sequenceId == 41 &&
                it.globalIndex == 9 &&
                it.x == 172 &&
                it.y == 217
        }
        val untouched = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }

        val edit = FaceEditor.remapPairSequence(
            source = source,
            entryBasename = "style0.bin",
            globalIndex = donor.globalIndex,
            originalSequenceId = donor.sequenceId,
            x = donor.x,
            y = donor.y,
            newSequenceId = 14,
        )

        val after = FaceRecordParser.scanWidgets(
            edit.container.entryByBasename("style0.bin"),
        )
        assertEquals(1, after.count {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 9 &&
                it.sequenceId == 14 &&
                it.x == 172 &&
                it.y == 217
        })
        assertEquals(0, after.count {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == 9 &&
                it.sequenceId == 41
        })
        assertEquals(1, edit.changedPayloadBytes)
        assertEquals(listOf("style0.bin"), edit.changedStyles)
        untouched.forEach { (name, beforeBytes) ->
            assertArrayEquals(beforeBytes, edit.container.entryByBasename(name).data)
        }
        assertEquals(source.fileSize, edit.container.fileSize)
        assertTrue(edit.container.validate().isValid)
    }

    @Test
    fun rejectsZeroOrAmbiguousPairIdentity() {
        val source = real00049()
        expectFormatFailure("expected exactly one Pair") {
            FaceEditor.remapPairSequence(
                source = source,
                entryBasename = "style0.bin",
                globalIndex = 999,
                originalSequenceId = 41,
                x = 172,
                y = 217,
                newSequenceId = 14,
            )
        }

        val duplicate = duplicateStyle0PairIdentity(source)
        expectFormatFailure("expected exactly one Pair") {
            FaceEditor.remapPairSequence(
                source = duplicate,
                entryBasename = "style0.bin",
                globalIndex = 9,
                originalSequenceId = 41,
                x = 172,
                y = 217,
                newSequenceId = 14,
            )
        }
    }

    @Test
    fun rejectsNonPairIdentityInvalidSequenceAndNoOp() {
        val source = real00049()
        expectFormatFailure("expected exactly one Pair") {
            FaceEditor.remapPairSequence(
                source = source,
                entryBasename = "style0.bin",
                globalIndex = 3,
                originalSequenceId = 2,
                x = 32,
                y = 93,
                newSequenceId = 14,
            )
        }
        for (invalid in listOf(-1, 256)) {
            expectFormatFailure("sequence id must be in 0..255") {
                FaceEditor.remapPairSequence(
                    source = source,
                    entryBasename = "style0.bin",
                    globalIndex = 9,
                    originalSequenceId = 41,
                    x = 172,
                    y = 217,
                    newSequenceId = invalid,
                )
            }
        }
        expectFormatFailure("already uses sequence 41") {
            FaceEditor.remapPairSequence(
                source = source,
                entryBasename = "style0.bin",
                globalIndex = 9,
                originalSequenceId = 41,
                x = 172,
                y = 217,
                newSequenceId = 41,
            )
        }
    }

    private fun real00049(): Fit3Container {
        val stream = javaClass.getResourceAsStream(
            "/fixtures/SM-R390_00049_256x402.bin",
        ) ?: fail("real Samsung 00049 fixture must be staged by CI")
        return Fit3Container.parse(stream.readBytes()).also {
            assertTrue(it.validate().isValid)
        }
    }

    private fun duplicateStyle0PairIdentity(source: Fit3Container): Fit3Container {
        val style = source.entryByBasename("style0.bin")
        val records = FaceRecordParser.scanWidgets(style)
        val target = records.single {
            it.widgetType == WIDGET_PAIR && it.globalIndex == 9 && it.sequenceId == 41
        }
        val donor = records.single {
            it.widgetType == WIDGET_PAIR && it.globalIndex == 15 && it.sequenceId == 29
        }
        val bytes = source.toByteArray()
        val base = style.offset + donor.recordOffset
        val indexAndSize = bytes.u32(base + 0x0C)
        bytes.putU32(base + 0x04, target.sequenceId.toLong())
        bytes.putU32(
            base + 0x0C,
            (target.globalIndex.toLong() shl 16) or (indexAndSize and 0xFFFF),
        )
        bytes.putU16(base + 0x18, target.x and 0xFFFF)
        bytes.putU16(base + 0x1A, target.y and 0xFFFF)

        val entryCrc = Crc16.ccittFalse(bytes, style.offset, style.end)
        val checksumOffset = CONTAINER_HEADER_SIZE +
            style.index * DIRECTORY_ENTRY_SIZE + 72
        bytes.putU16(checksumOffset, entryCrc)
        bytes.putU16(16, Crc16.ccittFalse(bytes, CONTAINER_HEADER_SIZE, bytes.size))
        return Fit3Container.parse(bytes).also { assertTrue(it.validate().isValid) }
    }

    private fun expectFormatFailure(messagePart: String, block: () -> Unit) {
        try {
            block()
            fail("expected Fit3FormatException containing: $messagePart")
        } catch (error: Fit3FormatException) {
            assertTrue(
                "actual message: ${error.message}",
                error.message.orEmpty().contains(messagePart),
            )
        }
    }
}
