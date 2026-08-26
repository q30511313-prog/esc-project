#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def replace(path: str, old: str, new: str) -> None:
    p = root / path
    text = p.read_text()
    count = text.count(old)
    if count < 1:
        raise SystemExit(f"{path}: expected patch anchor, found {count}")
    p.write_text(text.replace(old, new, 1))

# Shared palette imports for the already-patched Sprite and Pair controls.
replace(
    "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt",
    "import dev.fitface.studio.core.model.ImagePlacement\n",
    "import dev.fitface.studio.core.model.ImagePlacement\nimport dev.fitface.studio.core.model.LcdPalette\n",
)
replace(
    "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt",
    "import dev.fitface.studio.core.model.ImagePlacement\n",
    "import dev.fitface.studio.core.model.ImagePlacement\nimport dev.fitface.studio.core.model.LcdPalette\n",
)

# Move the approved experimental tint from C9CECB to the cooler AEB4B2.
vm = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt"
replace(vm, "                red = 0xC9,\n", "                red = LcdPalette.SILVER_RED,\n")
replace(vm, "                green = 0xCE,\n", "                green = LcdPalette.SILVER_GREEN,\n")
replace(vm, "                blue = 0xCB,\n", "                blue = LcdPalette.SILVER_BLUE,\n")

ui = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"
# Both Sprite and VALUE buttons use the same label after the old LCD patch.
text = (root / ui).read_text()
text = text.replace("LCD Silver #C9CECB", "LCD Silver #AEB4B2")
text = text.replace("0xFFC9_CECB.toInt()", "LcdPalette.SILVER_ARGB")
(root / ui).write_text(text)

# Expose exactly-one explicit opaque color from a Composite. This follows the
# independent parser's rule: ignore 0xFFFFFFFF and FFFF-high sentinel/control words.
records = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt"
replace(
    records,
    '''            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
                pairColor != null
            val referencedImages = referencedImages(it, imagesByRelativeOffset)
''',
    '''            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
                pairColor != null
            val compositeColorIndices = if (it.widgetType == WIDGET_COMP) {
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
            val referencedImages = referencedImages(it, imagesByRelativeOffset)
''',
)
replace(
    records,
    '''                colorArgb = pairColor.takeIf { canEditPair },
                pairBindingIndex = pairBindingIndex,
''',
    '''                colorArgb = when {
                    canEditPair -> pairColor
                    canEditComposite -> compositeColor
                    else -> null
                },
                pairBindingIndex = pairBindingIndex,
''',
)
replace(
    records,
    '''                    canEditPair -> "Drag to move; choose an opaque Pair color below"
                    canResizeSprite -> resizeMessage(resizePool, records, imagesByRelativeOffset, it)
''',
    '''                    canEditPair -> "Drag to move; choose an opaque Pair color below"
                    canEditComposite ->
                        "Drag to move; choose the Composite's explicit opaque text color below"
                    canResizeSprite -> resizeMessage(resizePool, records, imagesByRelativeOffset, it)
''',
)

# Low-level Composite edit: patch only the one proven color word; geometry, data
# bindings, glyph layout and record size are kept verbatim.
editor = "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
replace(
    editor,
    '''    fun replaceBackgrounds(
''',
    '''    fun recolorCompositeWidgetAcrossStyles(
        source: Fit3Container,
        entryBasenames: List<String>,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        colorArgb: Int,
    ): ContainerEdit {
        requireEditable(source)
        if (colorArgb ushr 24 != 0xFF) {
            throw Fit3FormatException("Composite widget color must be opaque ARGB")
        }
        fun colorWordIndex(record: WidgetRecord): Int? {
            val candidates = record.words.mapIndexedNotNull { index, word ->
                index.takeIf {
                    word != 0xFFFF_FFFFL &&
                        word ushr 16 != 0xFFFFL &&
                        word ushr 24 == 0xFFL
                }
            }
            return candidates.singleOrNull()
        }
        val resolved = StyleWidgetMatch.resolve(source, entryBasenames) { _, records ->
            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_COMP &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
        }
        if (colorWordIndex(resolved.first().second) == null) {
            throw Fit3FormatException(
                "Composite widget does not expose exactly one explicit opaque color word",
            )
        }
        // Sibling styles are best-effort: an ambiguous sibling keeps its own bytes.
        val targets = resolved.mapNotNull { (entry, record) ->
            colorWordIndex(record)?.let { index -> Triple(entry, record, index) }
        }
        val output = source.toByteArray()
        val before = output.copyOf()
        var changed = 0
        val changedEntries = mutableListOf<ContainerEntry>()
        targets.forEach { (entry, record, wordIndex) ->
            val start = entry.offset + record.recordOffset + WIDGET_FIXED_SIZE + wordIndex * 4
            output.putU32(start, colorArgb.toLong() and 0xFFFF_FFFFL)
            val entryChanged = (start until start + 4).count { before[it] != output[it] }
            if (entryChanged > 0) {
                changed += entryChanged
                changedEntries += entry
            }
        }
        if (changed == 0) {
            throw Fit3FormatException("Composite widget already uses that color")
        }
        return finalize(source, output, changedEntries, changed)
    }

    fun replaceBackgrounds(
''',
)

# Repository API.
models = "core/model/src/main/kotlin/dev/fitface/studio/core/model/Models.kt"
replace(
    models,
    '''    suspend fun moveWidget(
''',
    '''    suspend fun recolorCompositeWidget(
        styleName: String,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        colorArgb: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot

    suspend fun moveWidget(
''',
)

repo = "core/data/src/main/kotlin/dev/fitface/studio/core/data/WatchFaceRepositoryImpl.kt"
replace(
    repo,
    '''    override suspend fun moveWidget(
''',
    '''    override suspend fun recolorCompositeWidget(
        styleName: String,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        colorArgb: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot = withContext(Dispatchers.Default) {
        mutex.withLock {
            val current = requireSession()
            val styleNames = current.targetStyleNames(styleName, applyToAllStyles)
            val edit = FaceEditor.recolorCompositeWidgetAcrossStyles(
                source = current.currentContainer,
                entryBasenames = styleNames,
                globalIndex = globalIndex,
                sequenceId = sequenceId,
                x = x,
                y = y,
                colorArgb = colorArgb,
            )
            commit(
                current,
                edit.container,
                EditAuditSummary(
                    edit.changedPayloadBytes,
                    edit.changedStyles,
                    operation = if (applyToAllStyles) {
                        "Composite text color changed across compatible styles"
                    } else {
                        "Composite text color changed on selected style"
                    },
                ),
                styleName,
            )
        }
    }

    override suspend fun moveWidget(
''',
)

# Route the already-existing color control to Pair or Composite based on type.
replace(
    vm,
    '''    fun setSelectedWidgetColor(colorArgb: Int) {
        val snapshot = mutableState.value.snapshot ?: return
        val selected = snapshot.widgets.singleOrNull {
            it.globalIndex == mutableState.value.selectedWidgetIndex
        } ?: return
        if (selected.colorArgb == null || selected.colorArgb == colorArgb) return
        operate {
            repository.recolorPairWidget(
                styleName = snapshot.selectedStyle,
                globalIndex = selected.globalIndex,
                sequenceId = selected.sequenceId,
                x = selected.x,
                y = selected.y,
                colorArgb = colorArgb,
                applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
            )
        }
    }
''',
    '''    fun setSelectedWidgetColor(colorArgb: Int) {
        val snapshot = mutableState.value.snapshot ?: return
        val selected = snapshot.widgets.singleOrNull {
            it.globalIndex == mutableState.value.selectedWidgetIndex
        } ?: return
        if (selected.colorArgb == null || selected.colorArgb == colorArgb) return
        operate {
            when (selected.type) {
                5 -> repository.recolorPairWidget(
                    styleName = snapshot.selectedStyle,
                    globalIndex = selected.globalIndex,
                    sequenceId = selected.sequenceId,
                    x = selected.x,
                    y = selected.y,
                    colorArgb = colorArgb,
                    applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
                )
                13 -> repository.recolorCompositeWidget(
                    styleName = snapshot.selectedStyle,
                    globalIndex = selected.globalIndex,
                    sequenceId = selected.sequenceId,
                    x = selected.x,
                    y = selected.y,
                    colorArgb = colorArgb,
                    applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
                )
                else -> throw IllegalStateException("Selected widget has no editable text color")
            }
        }
    }
''',
)

# The full-width silver button for Pair/Composite now uses the common palette.
replace(ui, "onClick = { onColor(0xFFC9_CECB.toInt()) },", "onClick = { onColor(LcdPalette.SILVER_ARGB) },") if "0xFFC9_CECB.toInt()" in (root / ui).read_text() else None

# Distinguish this integrated build from the previous hardware-tested one.
replace(
    "app/src/main/res/values/strings.xml",
    '<string name="app_name">FitFace Studio LCD Test</string>',
    '<string name="app_name">FitFace Studio LCD Composite</string>',
)

print("cool LCD + Composite color patch applied")
