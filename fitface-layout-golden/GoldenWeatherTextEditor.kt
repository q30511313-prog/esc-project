package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.WATCH_CONTAINER_BYTE_CEILING
import java.io.ByteArrayOutputStream
import java.nio.charset.StandardCharsets
import kotlin.math.abs

/**
 * Adds live Korean weather text to Samsung 00049 without touching weather rasters.
 *
 * The stock seq69 Sprite remains the authoritative 24-frame icon. The remaining
 * pristine numeric Pair g17 is repurposed to the same seq69 data source and points at
 * 24 appended Korean locale groups. Samsung stock faces contain multiple precedents
 * where a Sprite and Pair consume one sequence simultaneously, so this keeps the
 * icon/text state synchronized while remaining image-count-neutral.
 */
object GoldenWeatherTextEditor {
    private const val LOCALE_HEADER_SIZE = 0x18
    private const val AMPM_GROUP_COUNT = 14
    private const val WEATHER_GROUP_BASE = 14
    private const val WEATHER_BINDING_INDEX = 2
    private const val WEATHER_PAIR_WORD2 = 0x0002000E

    val labelsKo: List<String> = listOf(
        "맑음", "구름조금", "흐림", "안개",
        "비", "비", "비", "소나기",
        "뇌우", "뇌우", "눈", "눈",
        "진눈깨비", "눈", "눈", "진눈깨비",
        "눈", "더움", "추움", "바람",
        "뇌우", "비", "바람", "회오리",
    )

    fun wire00049(
        source: Fit3Container,
        entryBasename: String,
        x: Int,
        y: Int,
    ): ContainerEdit {
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden weather text contract is defined only for style0.bin",
            )
        }
        requireValidAndTight(source)
        if (labelsKo.size != 24) {
            throw Fit3FormatException("Golden weather text must define exactly 24 labels")
        }

        val styleEntry = source.entryByBasename(entryBasename)
        val records = FaceRecordParser.scanWidgets(styleEntry)
        val weatherSprite = records.singleOrNull {
            it.globalIndex == 7 &&
                it.widgetType == WIDGET_SPRITE &&
                it.sequenceId == 69 &&
                it.x == 180 &&
                it.y == 102 &&
                it.words.size == 24
        } ?: throw Fit3FormatException(
            "Golden weather Sprite g7/seq69@(180,102) with 24 frames is missing or ambiguous",
        )
        if (weatherSprite.words.size != labelsKo.size) {
            throw Fit3FormatException(
                "Golden weather label count does not match the stock seq69 frame count",
            )
        }

        val donor = records.singleOrNull {
            it.globalIndex == 17 &&
                it.widgetType == WIDGET_PAIR &&
                it.sequenceId == 115 &&
                it.x == 179 &&
                it.y == 360
        } ?: throw Fit3FormatException(
            "Golden weather text donor g17/seq115@(179,360) is missing or ambiguous",
        )
        val bindingWord = donor.words.getOrNull(1) ?: throw Fit3FormatException(
            "Golden weather text donor g17 has no binding/layout word",
        )
        if ((bindingWord.toInt() and 0xFF) != WEATHER_BINDING_INDEX ||
            donor.words.getOrNull(2) != 0x0002FFFFL
        ) {
            throw Fit3FormatException(
                "Golden weather text donor g17 must retain pristine binding2/FFFF locale wiring",
            )
        }

        val localeEntry = source.entryByBasename("font_ko.bin")
        val locale = appendWeatherGroups(localeEntry.data)
        val style = styleEntry.data.copyOf().also { bytes ->
            bytes.putU32(donor.recordOffset + 0x04, 69)
            bytes.putU16(donor.recordOffset + 0x18, x and 0xFFFF)
            bytes.putU16(donor.recordOffset + 0x1A, y and 0xFFFF)
            bytes.putU32(
                donor.recordOffset + WIDGET_FIXED_SIZE + 2 * 4,
                WEATHER_PAIR_WORD2,
            )
        }

        return rebuild(
            source = source,
            replacements = mapOf(
                localeEntry.index to locale,
                styleEntry.index to style,
            ),
            changedStyles = listOf(entryBasename),
        )
    }

    private fun appendWeatherGroups(data: ByteArray): ByteArray {
        if (data.size < LOCALE_HEADER_SIZE ||
            data.u32(0) != STYLE_MAGIC ||
            data.u32(4) != 0x1CL ||
            data.u32(8) != AMPM_GROUP_COUNT.toLong() ||
            data.copyOfRange(0x0C, LOCALE_HEADER_SIZE).any { it.toInt() != 0 }
        ) {
            throw Fit3FormatException(
                "Samsung 00049 font_ko.bin is not the proven 14-group AM/PM locale stage",
            )
        }

        val expected = listOf(
            "(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)",
            "°", "0123456789", "%", "  ", "1234", "오전", "오후",
        )
        val current = readGroups(data)
        if (current != expected) {
            throw Fit3FormatException(
                "Samsung 00049 font_ko.bin does not match the proven AM/PM locale sequence",
            )
        }

        val groups = (expected + labelsKo).map { it.toByteArray(StandardCharsets.UTF_8) }
        val descriptorEnd = LOCALE_HEADER_SIZE + groups.size * 8
        val output = ByteArray(descriptorEnd + groups.sumOf { it.size })
        data.copyInto(output, 0, 0, LOCALE_HEADER_SIZE)
        output.putU32(8, groups.size)

        var cursor = descriptorEnd
        groups.forEachIndexed { index, bytes ->
            val descriptor = LOCALE_HEADER_SIZE + index * 8
            output.putU32(descriptor, bytes.size)
            output.putU32(descriptor + 4, cursor)
            bytes.copyInto(output, cursor)
            cursor += bytes.size
        }
        if (readGroups(output).subList(WEATHER_GROUP_BASE, groups.size) != labelsKo) {
            throw Fit3FormatException("Golden weather locale ordering is inconsistent")
        }
        return output
    }

    private fun readGroups(data: ByteArray): List<String> {
        val count = data.u32(8).checkedInt("locale group count")
        val descriptorEnd = LOCALE_HEADER_SIZE + count * 8
        if (descriptorEnd > data.size) {
            throw Fit3FormatException("Golden weather locale descriptors exceed entry size")
        }
        var expectedOffset = descriptorEnd
        return (0 until count).map { index ->
            val descriptor = LOCALE_HEADER_SIZE + index * 8
            val length = data.u32(descriptor).checkedInt("locale group length")
            val offset = data.u32(descriptor + 4).checkedInt("locale group offset")
            if (offset != expectedOffset || offset + length > data.size) {
                throw Fit3FormatException(
                    "Golden weather locale group $index is not tightly packed",
                )
            }
            expectedOffset += length
            String(data, offset, length, StandardCharsets.UTF_8)
        }.also {
            if (expectedOffset != data.size) {
                throw Fit3FormatException(
                    "Golden weather locale contains trailing or unaccounted bytes",
                )
            }
        }
    }

    private fun requireValidAndTight(source: Fit3Container) {
        val report = source.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "refusing Golden weather edit on invalid container: " +
                    report.errors.joinToString { it.code },
            )
        }
        var cursor = source.bodyOffset
        source.entries.forEach { entry ->
            if (entry.offset != cursor) {
                throw Fit3FormatException(
                    "Golden weather locale relocation requires a tightly packed body",
                )
            }
            cursor = entry.end
        }
        if (cursor != source.fileSize) {
            throw Fit3FormatException(
                "Golden weather locale relocation refuses trailing unreferenced bytes",
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
                "Golden weather text edit would exceed the Fit3 watch container limit",
            )
        }

        val parsed = Fit3Container.parse(assembled)
        val report = parsed.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden weather text rebuild failed validation: " +
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
            throw Fit3FormatException("Golden weather text edit would not change any bytes")
        }
        return ContainerEdit(
            container = parsed,
            changedPayloadBytes = changed,
            changedStyles = changedStyles,
        )
    }
}
