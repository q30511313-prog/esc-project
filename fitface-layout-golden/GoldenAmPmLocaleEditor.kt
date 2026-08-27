package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.WATCH_CONTAINER_BYTE_CEILING
import java.io.ByteArrayOutputStream
import java.nio.charset.StandardCharsets
import kotlin.math.abs

/**
 * Rebuilds only the Samsung 00049 Korean locale resources needed by live AM/PM.
 *
 * The stock 00049 locale does not contain `오전` / `오후`. This editor appends those
 * two groups, repurposes the existing `font_1.bin` WF_BMP binding as WF_AM_PM, and
 * wires the pristine style0 g9 Pair to the new locale base. All edits fail closed
 * against the exact v4.0.2 structures observed from the Samsung Store fixture.
 */
object GoldenAmPmLocaleEditor {
    private const val LOCALE_HEADER_SIZE = 0x18
    private const val ORIGINAL_GROUP_COUNT = 12
    private const val NEW_AM_GROUP_INDEX = 12
    private const val AM_PM_BINDING_INDEX = 1
    private const val AM_PM_PAIR_WORD2 = 0x0001000C

    fun wire00049(
        source: Fit3Container,
        entryBasename: String,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden AM/PM locale contract is defined only for style0.bin",
            )
        }
        requireValidAndTight(source)

        val styleEntry = source.entryByBasename(entryBasename)
        val donor = FaceRecordParser.scanWidgets(styleEntry).singleOrNull {
            it.globalIndex == 9 &&
                it.widgetType == WIDGET_PAIR &&
                it.sequenceId == 41 &&
                it.x == 172 &&
                it.y == 217 &&
                it.width == 45 &&
                it.height == 22
        } ?: throw Fit3FormatException(
            "Golden AM/PM locale donor g9/seq41@(172,217) 45x22 is missing or ambiguous",
        )
        val bindingWord = donor.words.getOrNull(1) ?: throw Fit3FormatException(
            "Golden AM/PM locale donor g9 has no binding/layout word",
        )
        if ((bindingWord.toInt() and 0xFF) != AM_PM_BINDING_INDEX ||
            donor.words.getOrNull(2) != 0x0001FFFFL
        ) {
            throw Fit3FormatException(
                "Golden AM/PM locale donor g9 does not expose pristine binding1/FFFF wiring",
            )
        }

        val localeEntry = source.entryByBasename("font_ko.bin")
        val fontEntry = source.entryByBasename("font_1.bin")
        val locale = rebuildKoreanLocale(localeEntry.data)
        val font = repurposeAmPmFont(fontEntry.data)
        val style = styleEntry.data.copyOf().also {
            it.putU32(
                donor.recordOffset + WIDGET_FIXED_SIZE + 2 * 4,
                AM_PM_PAIR_WORD2,
            )
        }

        return rebuild(
            source = source,
            replacements = mapOf(
                localeEntry.index to locale,
                fontEntry.index to font,
                styleEntry.index to style,
            ),
            changedStyles = listOf(entryBasename),
        )
    }

    private fun rebuildKoreanLocale(data: ByteArray): ByteArray {
        if (data.size != 174 ||
            data.u32(0) != STYLE_MAGIC ||
            data.u32(4) != 0x1CL ||
            data.u32(8) != ORIGINAL_GROUP_COUNT.toLong() ||
            data.copyOfRange(0x0C, LOCALE_HEADER_SIZE).any { it.toInt() != 0 }
        ) {
            throw Fit3FormatException(
                "Samsung 00049 font_ko.bin does not match the pristine 12-group locale header",
            )
        }

        val expected = listOf(
            "(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)",
            "°", "0123456789", "%", "  ", "1234",
        ).map { it.toByteArray(StandardCharsets.UTF_8) }

        val originalDescriptorEnd = LOCALE_HEADER_SIZE + ORIGINAL_GROUP_COUNT * 8
        var expectedOffset = originalDescriptorEnd
        expected.forEachIndexed { index, bytes ->
            val descriptor = LOCALE_HEADER_SIZE + index * 8
            val length = data.u32(descriptor).checkedInt("locale group length")
            val offset = data.u32(descriptor + 4).checkedInt("locale group offset")
            if (length != bytes.size || offset != expectedOffset ||
                offset + length > data.size ||
                !data.copyOfRange(offset, offset + length).contentEquals(bytes)
            ) {
                throw Fit3FormatException(
                    "Samsung 00049 font_ko.bin group $index is not the pristine locale sequence",
                )
            }
            expectedOffset += length
        }
        if (expectedOffset != data.size) {
            throw Fit3FormatException(
                "Samsung 00049 font_ko.bin has trailing or unaccounted locale bytes",
            )
        }

        val groups = expected + listOf(
            "오전".toByteArray(StandardCharsets.UTF_8),
            "오후".toByteArray(StandardCharsets.UTF_8),
        )
        val descriptorEnd = LOCALE_HEADER_SIZE + groups.size * 8
        val output = ByteArray(descriptorEnd + groups.sumOf { it.size })
        data.copyInto(output, destinationOffset = 0, startIndex = 0, endIndex = LOCALE_HEADER_SIZE)
        output.putU32(8, groups.size)

        var cursor = descriptorEnd
        groups.forEachIndexed { index, bytes ->
            val descriptor = LOCALE_HEADER_SIZE + index * 8
            output.putU32(descriptor, bytes.size)
            output.putU32(descriptor + 4, cursor)
            bytes.copyInto(output, cursor)
            cursor += bytes.size
        }
        if (groups[NEW_AM_GROUP_INDEX].decodeToString() != "오전" ||
            groups[NEW_AM_GROUP_INDEX + 1].decodeToString() != "오후"
        ) {
            throw Fit3FormatException("Golden AM/PM locale group ordering is inconsistent")
        }
        return output
    }

    private fun repurposeAmPmFont(data: ByteArray): ByteArray {
        if (data.size != 92 || data.u32(0x58) != 20L || fontRole(data) != "WF_BMP") {
            throw Fit3FormatException(
                "Samsung 00049 font_1.bin is not the pristine 20px WF_BMP binding",
            )
        }
        val output = data.copyOf()
        for (index in 0x48 until 0x58) output[index] = 0
        val role = "WF_AM_PM".toByteArray(StandardCharsets.US_ASCII)
        role.copyInto(output, 0x48)
        return output
    }

    private fun fontRole(data: ByteArray): String {
        val raw = data.copyOfRange(0x48, 0x58)
        val end = raw.indexOf(0).let { if (it < 0) raw.size else it }
        return String(raw, 0, end, StandardCharsets.US_ASCII)
    }

    private fun requireValidAndTight(source: Fit3Container) {
        val report = source.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "refusing Golden AM/PM locale edit on invalid container: " +
                    report.errors.joinToString { it.code },
            )
        }
        var cursor = source.bodyOffset
        source.entries.forEach { entry ->
            if (entry.offset != cursor) {
                throw Fit3FormatException(
                    "Golden AM/PM locale relocation requires a tightly packed body",
                )
            }
            cursor = entry.end
        }
        if (cursor != source.fileSize) {
            throw Fit3FormatException(
                "Golden AM/PM locale relocation refuses trailing unreferenced bytes",
            )
        }
    }

    private fun rebuild(
        source: Fit3Container,
        replacements: Map<Int, ByteArray>,
        changedStyles: List<String>,
    ): ContainerEdit {
        val original = source.toByteArray()
        val header = original.copyOfRange(0, CONTAINER_HEADER_SIZE)
        val directory = source.entries.map { it.rawRecord.copyOf() }
        val body = ByteArrayOutputStream()
        var cursor = source.bodyOffset

        source.entries.forEach { entry ->
            val payload = replacements[entry.index] ?: entry.data
            directory[entry.index].putU32(0x40, cursor)
            directory[entry.index].putU32(0x44, payload.size)
            directory[entry.index].putU16(0x48, Crc16.ccittFalse(payload))
            body.write(payload)
            cursor += payload.size
        }
        header.putU32(0x08, cursor - CONTAINER_HEADER_SIZE)

        val output = ByteArrayOutputStream()
        output.write(header)
        directory.forEach(output::write)
        output.write(body.toByteArray())
        val assembled = output.toByteArray()
        assembled.putU16(
            0x10,
            Crc16.ccittFalse(assembled, CONTAINER_HEADER_SIZE, assembled.size),
        )
        if (assembled.size > WATCH_CONTAINER_BYTE_CEILING) {
            throw Fit3FormatException(
                "Golden AM/PM locale edit would exceed the Fit3 watch container limit",
            )
        }

        val parsed = Fit3Container.parse(assembled)
        val report = parsed.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden AM/PM locale rebuild failed validation: " +
                    report.errors.joinToString { it.code },
            )
        }

        val changed = replacements.entries.sumOf { (index, bytes) ->
            val before = source.entries[index].data
            before.indices.take(minOf(before.size, bytes.size)).count {
                before[it] != bytes[it]
            } + abs(before.size - bytes.size)
        }
        if (changed == 0) {
            throw Fit3FormatException("Golden AM/PM locale edit would not change any bytes")
        }
        return ContainerEdit(
            container = parsed,
            changedPayloadBytes = changed,
            changedStyles = changedStyles,
        )
    }
}
