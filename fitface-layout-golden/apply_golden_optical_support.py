#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

anchor = '''    fun replaceBackgrounds(\n'''
method = '''    /**
     * Golden D1 only: recolour Samsung 00049 style0 temperature Composite.
     *
     * The generic Composite editor intentionally treats 0xFFFFFFFF as ambiguous,
     * because many Composite records use it as a sentinel. Real 00049 evidence is
     * narrower: g8/type13/seq0 uses live source 0xFFFF003E, binding 0x00080007 and
     * stores opaque white in the same words[13] colour slot that date/battery use.
     * All four stock styles preserve that exact identity, so only this one proven
     * post-layout record may cross the generic white/sentinel guard.
     */
    fun recolorGolden00049TemperatureComposite(
        source: Fit3Container,
        entryBasename: String,
        colorArgb: Int,
    ): ContainerEdit {
        requireEditable(source)
        if (entryBasename != "style0.bin") {
            throw Fit3FormatException(
                "Golden 00049 temperature optical edit is defined only for style0.bin",
            )
        }
        if (colorArgb ushr 24 != 0xFF) {
            throw Fit3FormatException("Golden temperature colour must be opaque ARGB")
        }
        val entry = source.entryByBasename(entryBasename)
        val record = FaceRecordParser.scanWidgets(entry).singleOrNull {
            it.globalIndex == 8 &&
                it.widgetType == WIDGET_COMP &&
                it.sequenceId == 0 &&
                it.x == 171 &&
                it.y == 260 &&
                it.width == 51 &&
                it.height == 22
        } ?: throw Fit3FormatException(
            "Golden 00049 temperature g8/type13/seq0@(171,260) 51x22 is missing or ambiguous",
        )
        if (record.words.getOrNull(0) != 0xFFFF003EL ||
            record.words.getOrNull(1) != 0x00080007L ||
            record.words.getOrNull(13) != 0xFFFF_FFFFL
        ) {
            throw Fit3FormatException(
                "Golden 00049 temperature does not expose the proven white words[13] colour slot",
            )
        }

        val output = source.toByteArray()
        val start = entry.offset + record.recordOffset + WIDGET_FIXED_SIZE + 13 * 4
        val before = output.copyOfRange(start, start + 4)
        output.putU32(start, colorArgb.toLong() and 0xFFFF_FFFFL)
        val changed = (0 until 4).count { before[it] != output[start + it] }
        if (changed == 0) {
            throw Fit3FormatException("Golden 00049 temperature already uses that colour")
        }
        return finalize(source, output, listOf(entry), changed)
    }

'''

count = text.count(anchor)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one replaceBackgrounds anchor, found {count}")

path.write_text(text.replace(anchor, method + anchor, 1))
print("Golden 00049 exact temperature optical support applied")
