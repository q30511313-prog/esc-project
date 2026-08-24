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

editor = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"

# VALUE/type-5: right-anchored records are stored with a negative far-edge X while
# the editor shows the drawn/display X. Match by stable record identity, never by
# geometry from two different coordinate spaces.
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

# COMPOSITE/type-13: the hardware-tested format evidence pins the theme color to
# record +0x58 = words[13]. Do not guess by scanning for ARGB-looking words.
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
            val canEditComposite = it.widgetType == WIDGET_COMP && compositeColor != null
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

# IMAGE/type-1: keep the raster tint implementation, but identify the selected record
# by stable identity just like VALUE. The raster itself is still target.unknown20 and
# only its RGB565 sample bytes are modified.
replace(
    editor,
    '''            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_STATIC &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
''',
    '''            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_STATIC &&
                    it.sequenceId == sequenceId
            }
''',
)

# User-approved final Casio reference color. Palette values come from LcdPalette;
# this only keeps the inspector label truthful.
ui = root / "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"
text = ui.read_text().replace("LCD Silver #AEB4B2", "LCD Gray #9F9E99")
ui.write_text(text)

print("hardware VALUE/COMPOSITE/IMAGE color fixes applied")
