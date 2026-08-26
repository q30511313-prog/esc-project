#!/usr/bin/env python3
"""Apply the narrowly-scoped Golden layout format additions to FitFace.

The patch is intentionally fail-closed: it only inserts a style-scoped Pair
sequence remapper into FaceEditor and refuses to run if the source shape is not
what this patch was written against or if the method already exists.
"""

from pathlib import Path
import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_format_patch.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
    text = path.read_text()

    if "fun remapPairSequence(" in text:
        raise SystemExit("FaceEditor.remapPairSequence already exists; refusing duplicate patch")

    anchor = "object FaceEditor {\n"
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"FaceEditor object anchor count must be 1, found {count}")

    method = r'''object FaceEditor {
    /**
     * Golden-layout primitive: rebinds exactly one existing type-5 Pair widget in
     * exactly one named style to another firmware sequence id.
     *
     * This is deliberately same-size and Pair-only. The caller must supply the
     * original global index, sequence and coordinates so an unexpected stock-face
     * revision fails closed instead of editing a look-alike record.
     */
    fun remapPairSequence(
        source: Fit3Container,
        entryBasename: String,
        globalIndex: Int,
        originalSequenceId: Int,
        x: Int,
        y: Int,
        newSequenceId: Int,
    ): ContainerEdit {
        requireEditable(source)
        if (newSequenceId !in 0..255) {
            throw Fit3FormatException("Pair sequence id must be in 0..255")
        }
        if (newSequenceId == originalSequenceId) {
            throw Fit3FormatException(
                "Pair widget already uses sequence $originalSequenceId",
            )
        }

        val entry = source.entryByBasename(entryBasename)
        val matches = FaceRecordParser.scanWidgets(entry).filter {
            it.widgetType == WIDGET_PAIR &&
                it.globalIndex == globalIndex &&
                it.sequenceId == originalSequenceId &&
                it.x == x &&
                it.y == y
        }
        if (matches.size != 1) {
            throw Fit3FormatException(
                "$entryBasename: expected exactly one Pair widget with identity " +
                    "global=$globalIndex sequence=$originalSequenceId x=$x y=$y, " +
                    "found ${matches.size}",
            )
        }

        val record = matches.single()
        val output = source.toByteArray()
        val before = output.copyOf()
        val sequenceOffset = entry.offset + record.recordOffset + 0x04
        output.putU32(sequenceOffset, newSequenceId.toLong())
        val changed = (sequenceOffset until sequenceOffset + 4)
            .count { before[it] != output[it] }
        if (changed == 0) {
            throw Fit3FormatException("Pair sequence remap would not change any bytes")
        }
        return finalize(source, output, listOf(entry), changed)
    }
'''

    path.write_text(text.replace(anchor, method, 1))
    print("Golden style-scoped Pair sequence remap patch applied")


if __name__ == "__main__":
    main()
