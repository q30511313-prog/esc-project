package dev.fitface.studio.core.format

import dev.fitface.studio.core.model.WATCH_CONTAINER_BYTE_CEILING
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import kotlin.math.abs

/**
 * Final hardware-only corrections proven from the first real Galaxy Fit3 D1 photos.
 *
 * Task 7/8 deliberately keep their logical 256x402 layout contracts untouched. The
 * Fit3 firmware applies sequence-specific offsets to the two hour Sprite records that
 * are not represented by FitFace's parser/preview. The real watch also rendered the
 * newly appended Korean strings as tofu while the stock WF_WEEK binding rendered
 * `(목)` correctly. This layer compensates only those hardware facts and patches the
 * old clean plate's date suffixes/static colon without changing the approved artwork
 * elsewhere.
 */
object GoldenD1HardwareCorrections {
    const val INPUT_PLATE_RGB565_SHA256 =
        "e12a722dc7a1e51bde71c9ffa375e0ec9443521e9da9feaef77819ee8e939c3e"
    const val OUTPUT_PLATE_RGB565_SHA256 =
        "0d70da8a8047ef439ec43041a737ae02cac28610c34b43708a13d736274d0bc7"

    // Perspective-normalized measurements from two independent real-watch photos.
    // g3: firmware x bias ~= -76 px. g4: x bias ~= -50 px, y bias ~= +95 px.
    private const val HOUR_TENS_RECORD_X = 153
    private const val HOUR_TENS_RECORD_Y = 139
    private const val HOUR_ONES_RECORD_X = 156
    private const val HOUR_ONES_RECORD_Y = 44

    private const val KOREAN_TEXT_BINDING = 4 // stock WF_WEEK; hardware-proven by `(목)`
    private const val AM_PM_WORD2 = 0x0004000CL
    private const val WEATHER_WORD2 = 0x0004000EL

    private const val WIDTH = 256
    private const val HEIGHT = 402
    private const val COLON_SHIFT_X = 16

    private data class Box(val x0: Int, val y0: Int, val x1: Int, val y1: Int)

    private val reconstructBoxes = listOf(
        Box(109, 47, 122, 64), // year suffix from the independent-date artwork
        Box(143, 47, 158, 64), // month suffix
        Box(179, 47, 192, 64), // day suffix
        Box(114, 151, 130, 199), // old static colon
    )
    private val colonDotBoxes = listOf(
        Box(116, 153, 128, 167),
        Box(116, 183, 128, 197),
    )

    fun compile(source: Fit3Container): ContainerEdit {
        val report = source.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "refusing Golden D1 hardware correction on invalid container: " +
                    report.errors.joinToString { it.code },
            )
        }
        if (GoldenD1CleanPlate.RAW_RGB565_SHA256 != INPUT_PLATE_RGB565_SHA256) {
            throw Fit3FormatException("Golden D1 logical clean-plate identity drifted")
        }

        val inputStyle = source.entryByBasename("style0.bin")
        val inputRecords = FaceRecordParser.scanWidgets(inputStyle)
        requireWidget(inputRecords, 3, WIDGET_SPRITE, 2, 77, 139)
        requireWidget(inputRecords, 4, WIDGET_SPRITE, 3, 106, 139)
        val amPm = requireWidget(inputRecords, 9, WIDGET_PAIR, 5, 48, 120)
        val weather = requireWidget(inputRecords, 17, WIDGET_PAIR, 69, 112, 301)
        if ((amPm.words.getOrNull(1)?.toInt()?.and(0xFF)) != 1 ||
            amPm.words.getOrNull(2) != 0x0001000CL
        ) {
            throw Fit3FormatException("Golden D1 AM/PM is not at the proven Task 8 binding stage")
        }
        if ((weather.words.getOrNull(1)?.toInt()?.and(0xFF)) != 2 ||
            weather.words.getOrNull(2) != 0x0002000EL
        ) {
            throw Fit3FormatException("Golden D1 weather text is not at the proven Task 8 binding stage")
        }
        if (backgroundRgb565Sha256(source) != INPUT_PLATE_RGB565_SHA256) {
            throw Fit3FormatException("Golden D1 background is not the proven Task 8 clean plate")
        }

        val siblings = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }
        val beforeImageCount = FaceRecordParser.scanImages(inputStyle).size

        var current = source
        var changed = 0
        fun accept(edit: ContainerEdit) {
            current = edit.container
            changed += edit.changedPayloadBytes
        }

        accept(
            FaceEditor.moveWidget(
                source = current,
                entryBasename = "style0.bin",
                globalIndex = 3,
                widgetType = WIDGET_SPRITE,
                sequenceId = 2,
                x = HOUR_TENS_RECORD_X,
                y = HOUR_TENS_RECORD_Y,
            ),
        )
        accept(
            FaceEditor.moveWidget(
                source = current,
                entryBasename = "style0.bin",
                globalIndex = 4,
                widgetType = WIDGET_SPRITE,
                sequenceId = 3,
                x = HOUR_ONES_RECORD_X,
                y = HOUR_ONES_RECORD_Y,
            ),
        )
        accept(rebindKoreanTextPairs(current))
        accept(
            FaceEditor.replaceBackgroundInStyle(
                source = current,
                entryBasename = "style0.bin",
                width = WIDTH,
                height = HEIGHT,
                argb = hardwarePlateArgb(),
            ),
        )

        val outputStyle = current.entryByBasename("style0.bin")
        val outputRecords = FaceRecordParser.scanWidgets(outputStyle)
        requireWidget(outputRecords, 3, WIDGET_SPRITE, 2, HOUR_TENS_RECORD_X, HOUR_TENS_RECORD_Y)
        requireWidget(outputRecords, 4, WIDGET_SPRITE, 3, HOUR_ONES_RECORD_X, HOUR_ONES_RECORD_Y)
        val finalAmPm = requireWidget(outputRecords, 9, WIDGET_PAIR, 5, 48, 120)
        val finalWeather = requireWidget(outputRecords, 17, WIDGET_PAIR, 69, 112, 301)
        if ((finalAmPm.words[1].toInt() and 0xFF) != KOREAN_TEXT_BINDING ||
            finalAmPm.words[2] != AM_PM_WORD2
        ) {
            throw Fit3FormatException("Golden D1 AM/PM hardware text binding did not lock")
        }
        if ((finalWeather.words[1].toInt() and 0xFF) != KOREAN_TEXT_BINDING ||
            finalWeather.words[2] != WEATHER_WORD2
        ) {
            throw Fit3FormatException("Golden D1 weather hardware text binding did not lock")
        }
        if (backgroundRgb565Sha256(current) != OUTPUT_PLATE_RGB565_SHA256) {
            throw Fit3FormatException("Golden D1 hardware clean-plate hash did not lock")
        }
        if (FaceRecordParser.scanImages(outputStyle).size != beforeImageCount) {
            throw Fit3FormatException("Golden D1 hardware correction changed style0 image count")
        }
        siblings.forEach { (name, bytes) ->
            if (!bytes.contentEquals(current.entryByBasename(name).data)) {
                throw Fit3FormatException("Golden D1 hardware correction changed sibling $name")
            }
        }
        val finalReport = current.validate()
        if (!finalReport.isValid) {
            throw Fit3FormatException(
                "Golden D1 hardware correction failed validation: " +
                    finalReport.errors.joinToString { it.code },
            )
        }
        if (current.fileSize > WATCH_CONTAINER_BYTE_CEILING) {
            throw Fit3FormatException("Golden D1 hardware correction exceeds watch container limit")
        }
        if (changed <= 0) {
            throw Fit3FormatException("Golden D1 hardware correction changed no bytes")
        }
        return ContainerEdit(
            container = current,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin"),
        )
    }

    private fun requireWidget(
        records: List<WidgetRecord>,
        globalIndex: Int,
        type: Int,
        sequence: Int,
        x: Int,
        y: Int,
    ): WidgetRecord = records.singleOrNull {
        it.globalIndex == globalIndex &&
            it.widgetType == type &&
            it.sequenceId == sequence &&
            it.x == x &&
            it.y == y
    } ?: throw Fit3FormatException(
        "Golden D1 hardware identity g$globalIndex/type$type/seq$sequence@($x,$y) is missing or ambiguous",
    )

    private fun rebindKoreanTextPairs(source: Fit3Container): ContainerEdit {
        val style = source.entryByBasename("style0.bin")
        val records = FaceRecordParser.scanWidgets(style)
        val amPm = requireWidget(records, 9, WIDGET_PAIR, 5, 48, 120)
        val weather = requireWidget(records, 17, WIDGET_PAIR, 69, 112, 301)
        if ((amPm.words[1].toInt() and 0xFF) != 1 || amPm.words[2] != 0x0001000CL) {
            throw Fit3FormatException("Golden D1 AM/PM Pair is not pristine for hardware rebinding")
        }
        if ((weather.words[1].toInt() and 0xFF) != 2 || weather.words[2] != 0x0002000EL) {
            throw Fit3FormatException("Golden D1 weather Pair is not pristine for hardware rebinding")
        }

        val replacement = style.data.copyOf()
        fun patch(record: WidgetRecord, word2: Long) {
            val word1 = record.words[1]
            replacement.putU32(
                record.recordOffset + WIDGET_FIXED_SIZE + 4,
                (word1 and 0xFFFF_FF00L) or KOREAN_TEXT_BINDING.toLong(),
            )
            replacement.putU32(record.recordOffset + WIDGET_FIXED_SIZE + 8, word2)
        }
        patch(amPm, AM_PM_WORD2)
        patch(weather, WEATHER_WORD2)
        return rebuildStyleOnly(source, style.index, replacement)
    }

    private fun rebuildStyleOnly(
        source: Fit3Container,
        replacementIndex: Int,
        replacement: ByteArray,
    ): ContainerEdit {
        val original = source.toByteArray()
        val header = original.copyOfRange(0, CONTAINER_HEADER_SIZE)
        val directory = source.entries.map { it.rawRecord.copyOf() }
        val body = ByteArrayOutputStream()
        var cursor = source.bodyOffset

        source.entries.forEach { entry ->
            val payload = if (entry.index == replacementIndex) replacement else entry.data
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
            throw Fit3FormatException("Golden D1 hardware text rebinding exceeds watch limit")
        }
        val parsed = Fit3Container.parse(assembled)
        val validation = parsed.validate()
        if (!validation.isValid) {
            throw Fit3FormatException(
                "Golden D1 hardware text rebinding failed validation: " +
                    validation.errors.joinToString { it.code },
            )
        }

        val before = source.entries[replacementIndex].data
        val changed = before.indices.take(minOf(before.size, replacement.size)).count {
            before[it] != replacement[it]
        } + abs(before.size - replacement.size)
        if (changed == 0) {
            throw Fit3FormatException("Golden D1 hardware text rebinding changed no bytes")
        }
        return ContainerEdit(
            container = parsed,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin"),
        )
    }

    private fun hardwarePlateArgb(): IntArray {
        val source = GoldenD1CleanPlate.argb()
        if (source.size != WIDTH * HEIGHT) {
            throw Fit3FormatException("Golden D1 logical clean plate dimensions drifted")
        }
        val output = source.copyOf()
        reconstructBoxes.forEach { reconstructRegion(output, it) }
        colonDotBoxes.forEach { box ->
            for (y in box.y0 until box.y1) {
                for (x in box.x0 until box.x1) {
                    output[y * WIDTH + x + COLON_SHIFT_X] = source[y * WIDTH + x]
                }
            }
        }
        if (rgb565Sha256(output) != OUTPUT_PLATE_RGB565_SHA256) {
            throw Fit3FormatException("Golden D1 hardware plate reconstruction hash drifted")
        }
        return output
    }

    private fun reconstructRegion(pixels: IntArray, box: Box) {
        val width = box.x1 - box.x0
        val height = box.y1 - box.y0
        if (width <= 0 || height <= 0) {
            throw Fit3FormatException("Golden D1 hardware reconstruction box is empty")
        }
        val original = IntArray(width * height) { index ->
            val x = index % width
            val y = index / width
            pixels[(box.y0 + y) * WIDTH + box.x0 + x]
        }
        val baseMask = BooleanArray(width * height)
        original.forEachIndexed { index, color ->
            val red = color ushr 16 and 0xFF
            val green = color ushr 8 and 0xFF
            val blue = color and 0xFF
            val luminance = (77 * red + 150 * green + 29 * blue + 128) / 256
            baseMask[index] = luminance >= 28
        }
        val mask = BooleanArray(width * height)
        for (y in 0 until height) {
            for (x in 0 until width) {
                if (!baseMask[y * width + x]) continue
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        val nx = x + dx
                        val ny = y + dy
                        if (nx in 0 until width && ny in 0 until height) {
                            mask[ny * width + nx] = true
                        }
                    }
                }
            }
        }

        for (y in 0 until height) {
            var x = 0
            while (x < width) {
                if (!mask[y * width + x]) {
                    x++
                    continue
                }
                val start = x
                while (x < width && mask[y * width + x]) x++
                val end = x

                var left = start - 1
                while (left >= 0 && mask[y * width + left]) left--
                var right = end
                while (right < width && mask[y * width + right]) right++

                when {
                    left >= 0 && right < width -> {
                        val span = right - left
                        val leftColor = original[y * width + left]
                        val rightColor = original[y * width + right]
                        for (targetX in start until end) {
                            val distance = targetX - left
                            fun blend(shift: Int): Int {
                                val a = leftColor ushr shift and 0xFF
                                val b = rightColor ushr shift and 0xFF
                                return (a * (span - distance) + b * distance + span / 2) / span
                            }
                            val red = blend(16)
                            val green = blend(8)
                            val blue = blend(0)
                            pixels[(box.y0 + y) * WIDTH + box.x0 + targetX] =
                                (0xFF shl 24) or (red shl 16) or (green shl 8) or blue
                        }
                    }
                    left >= 0 -> {
                        val color = original[y * width + left]
                        for (targetX in start until end) {
                            pixels[(box.y0 + y) * WIDTH + box.x0 + targetX] = color
                        }
                    }
                    right < width -> {
                        val color = original[y * width + right]
                        for (targetX in start until end) {
                            pixels[(box.y0 + y) * WIDTH + box.x0 + targetX] = color
                        }
                    }
                    else -> throw Fit3FormatException(
                        "Golden D1 hardware reconstruction has no row background anchor",
                    )
                }
            }
        }
    }

    private fun backgroundRgb565Sha256(container: Fit3Container): String {
        val entry = container.entryByBasename("style0.bin")
        val image = FaceRecordParser.backgroundImage(entry)
            ?: throw Fit3FormatException("Golden D1 style0 has no background raster")
        if (image.width != WIDTH || image.height != HEIGHT || image.format != IMAGE_RGB565) {
            throw Fit3FormatException("Golden D1 style0 background schema drifted")
        }
        val start = image.samplesOffset
        val end = start + WIDTH * HEIGHT * 2
        return sha256(entry.data.copyOfRange(start, end))
    }

    private fun rgb565Sha256(argb: IntArray): String {
        val raw = ByteArray(argb.size * 2)
        argb.forEachIndexed { index, color ->
            val red = color ushr 16 and 0xFF
            val green = color ushr 8 and 0xFF
            val blue = color and 0xFF
            val rgb565 = ((red ushr 3) shl 11) or
                ((green ushr 2) shl 5) or
                (blue ushr 3)
            raw[index * 2] = rgb565.toByte()
            raw[index * 2 + 1] = (rgb565 ushr 8).toByte()
        }
        return sha256(raw)
    }

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256")
            .digest(bytes)
            .joinToString("") { byte -> "%02x".format(byte.toInt() and 0xFF) }
}
