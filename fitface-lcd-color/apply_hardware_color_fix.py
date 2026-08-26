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


def replace_in_function(path: str, function_name: str, old: str, new: str) -> None:
    p = root / path
    text = p.read_text()
    marker = f"    fun {function_name}("
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"{path}: function {function_name} not found")
    next_fun = text.find("\n    fun ", start + len(marker))
    end = len(text) if next_fun < 0 else next_fun
    block = text[start:end]
    count = block.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}:{function_name}: expected one patch anchor, found {count}"
        )
    block = block.replace(old, new, 1)
    p.write_text(text[:start] + block + text[end:])

editor = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
records = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt"
ui_path = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"

# VALUE/type-5: right-anchored records are stored with a negative far-edge X while
# the editor shows the drawn/display X. Match by stable record identity, never by
# geometry from two different coordinate spaces. Restrict this to recolor only so
# the already-working Pair binding experiment stays untouched.
replace_in_function(
    editor,
    "recolorPairWidgetAcrossStyles",
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

# VALUE/type-5 inspector exposure: sequenceId is a data-source selector, not a unique
# record ID. Samsung's style3 has several seq-0 VALUE records (#13-#17), each with its
# own opaque color word. Recoloring already resolves by globalIndex + type + sequence,
# so duplicate sequence IDs must not hide otherwise valid color controls.
replace(
    records,
    '''            val pairMatches = records.count { candidate ->
                candidate.widgetType == WIDGET_PAIR && candidate.sequenceId == it.sequenceId
            }
            val pairColor = it.words.firstOrNull()?.takeIf { word ->
                word ushr 24 == 0xFFL
            }?.toInt()
            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
                pairColor != null
''',
    '''            val pairColor = it.words.firstOrNull()?.takeIf { word ->
                word ushr 24 == 0xFFL
            }?.toInt()
            val canEditPair = it.widgetType == WIDGET_PAIR && pairColor != null
''',
)

# COMPOSITE/type-13: hardware format evidence pins the theme color to
# record +0x58 = words[13]. Do not guess by scanning for ARGB-looking words.
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

replace_in_function(
    editor,
    "recolorCompositeWidgetAcrossStyles",
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
replace_in_function(
    editor,
    "recolorCompositeWidgetAcrossStyles",
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
replace_in_function(
    editor,
    "recolorCompositeWidgetAcrossStyles",
    '''                "Composite widget does not expose exactly one explicit opaque color word",
''',
    '''                "Composite widget does not expose an opaque color at record +0x58",
''',
)

# IMAGE/type-1: keep the raster tint implementation, but identify the selected record
# by stable identity. The actual raster pointer remains target.unknown20 and only its
# RGB565 sample bytes are modified.
replace_in_function(
    editor,
    "recolorStaticWidgetAcrossStyles",
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

# The full-panel type-1 record is the background layer, not a tintable IMAGE widget.
# The format layer already refuses to rewrite it; mirror that safety rule in the
# Inspector so the user is never offered a button that can only fail.
replace(
    ui_path,
    '''        if (widget.type == 1 || widget.type == 3) {
''',
    '''        if ((widget.type == 1 && widget.placement != WidgetPlacement.BACKGROUND) ||
            widget.type == 3
        ) {
''',
)

# Kotlin's when expression must return EditorSnapshot from every branch because
# operate{} is typed that way. The preceding type guard is not enough for exhaustiveness.
# Add an explicit impossible branch without altering either raster recolor path.
vm = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt"
replace_in_function(
    vm,
    "setSelectedSpriteLcdSilver",
    '''                3 -> repository.recolorSpriteWidget(
                    styleName = snapshot.selectedStyle,
                    globalIndex = selected.globalIndex,
                    sequenceId = selected.sequenceId,
                    x = selected.x,
                    y = selected.y,
                    red = LcdPalette.SILVER_RED,
                    green = LcdPalette.SILVER_GREEN,
                    blue = LcdPalette.SILVER_BLUE,
                    applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
                )
            }
''',
    '''                3 -> repository.recolorSpriteWidget(
                    styleName = snapshot.selectedStyle,
                    globalIndex = selected.globalIndex,
                    sequenceId = selected.sequenceId,
                    x = selected.x,
                    y = selected.y,
                    red = LcdPalette.SILVER_RED,
                    green = LcdPalette.SILVER_GREEN,
                    blue = LcdPalette.SILVER_BLUE,
                    applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
                )
                else -> throw IllegalStateException("Selected widget has no raster LCD tint")
            }
''',
)

# User-approved final Casio reference color. Palette values come from LcdPalette;
# this only keeps the inspector label truthful.
ui = root / ui_path
text = ui.read_text().replace("LCD Silver #AEB4B2", "LCD Gray #9F9E99")
ui.write_text(text)

print("hardware VALUE/COMPOSITE/IMAGE color fixes applied")
