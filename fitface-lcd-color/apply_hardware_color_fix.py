#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def replace(path: str, old: str, new: str) -> None:
    p = root / path
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one patch anchor, found {count}")
    p.write_text(text.replace(old, new, 1))

# Pair/Value: the widget list exposes right-anchored Pair records in display-space
# coordinates, while the binary stores a negative right-edge inset. Color edits must
# identify the selected record by stable global index/type/sequence, not compare those
# two different coordinate spaces.
editor = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
replace(
    editor,
    '''            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_PAIR &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
''',
    '''            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_PAIR &&
                    it.sequenceId == sequenceId
            }
''',
)

# Composite color is not "whichever word looks like ARGB". The independently derived
# format and Samsung's own style variants pin it to record +0x58 = words[13].
records = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt"
replace(
    records,
    '''            val compositeColorIndices = if (it.widgetType == WIDGET_COMP) {
                it.words.mapIndexedNotNull { index, word ->
                    index.takeIf {
                        word != 0xFFFF_FFFFL &&
                            word ushr 16 != 0xFFFFL &&
                            word ushr 24 == 0xFFL
                    }
                }
            } else {
                emptyList()
            }
            val compositeColor = compositeColorIndices.singleOrNull()?.let { index ->
                it.words[index].toInt()
            }
            val canEditComposite = it.widgetType == WIDGET_COMP && compositeColor != null
''',
    '''            val compositeColor = if (it.widgetType == WIDGET_COMP) {
                it.words.getOrNull(13)?.takeIf { word ->
                    word != 0xFFFF_FFFFL && word ushr 24 == 0xFFL
                }?.toInt()
            } else {
                null
            }
            val canEditComposite = compositeColor != null
''',
)

replace(
    editor,
    '''        fun colorWordIndex(record: WidgetRecord): Int? {
            val candidates = record.words.mapIndexedNotNull { index, word ->
                index.takeIf {
                    word != 0xFFFF_FFFFL &&
                        word ushr 16 != 0xFFFFL &&
                        word ushr 24 == 0xFFL
                }
            }
            return candidates.singleOrNull()
        }
''',
    '''        fun colorWordIndex(record: WidgetRecord): Int? {
            if (record.widgetType != WIDGET_COMP) return null
            val word = record.words.getOrNull(13) ?: return null
            return 13.takeIf {
                word != 0xFFFF_FFFFL && word ushr 24 == 0xFFL
            }
        }
''',
)
replace(
    editor,
    '''            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_COMP &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
''',
    '''            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_COMP &&
                    it.sequenceId == sequenceId
            }
''',
)
replace(
    editor,
    '''                "Composite widget does not expose exactly one explicit opaque color word",
''',
    '''                "Composite widget does not expose an opaque color at record +0x58",
''',
)

print("hardware Pair anchor + exact Composite +0x58 color fixes applied")
