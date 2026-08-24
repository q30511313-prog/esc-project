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

# 1) Low-level edit: recolor the complete glyph pool shared by the selected Sprite.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt",
    '''    fun replaceBackgrounds(
''',
    '''    fun recolorSpriteWidgetAcrossStyles(
        source: Fit3Container,
        entryBasenames: List<String>,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        red: Int,
        green: Int,
        blue: Int,
    ): ContainerEdit {
        requireEditable(source)
        listOf(red, green, blue).forEach {
            if (it !in 0..255) throw Fit3FormatException("color channels must be 0..255")
        }
        val targets = StyleWidgetMatch.resolve(source, entryBasenames) { _, records ->
            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_SPRITE &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
        }
        val output = source.toByteArray()
        var changed = 0
        val changedEntries = mutableListOf<ContainerEntry>()
        targets.forEach { (entry, target) ->
            val records = FaceRecordParser.scanWidgets(entry)
            val images = FaceRecordParser.scanImages(entry)
            val firstImageOffset = images.firstOrNull()?.recordOffset
                ?: throw Fit3FormatException("${entry.basename}: Sprite has no image pool")
            val imagesByRelativeOffset = images.associateBy {
                (it.recordOffset - firstImageOffset).toLong()
            }
            val pool = FaceRecordParser.sharedFrameClosure(
                target,
                records,
                imagesByRelativeOffset,
            )
            val background = FaceRecordParser.backgroundImage(entry)?.index
            if (background != null && background in pool) {
                throw Fit3FormatException("${entry.basename}: Sprite pool reaches the background")
            }
            val poolImages = pool.sorted().map { imageIndex ->
                images.getOrNull(imageIndex) ?: throw Fit3FormatException(
                    "${entry.basename}: Sprite points outside the image pool",
                )
            }
            if (poolImages.any { it.format !in setOf(IMAGE_RGB565, IMAGE_RGB565_ALPHA) }) {
                throw Fit3FormatException(
                    "${entry.basename}: LCD tint supports RGB565 and RGB565+A Sprite frames only",
                )
            }
            var entryChanged = 0
            poolImages.forEach { image ->
                repeat(image.width * image.height) { pixel ->
                    val absolute = entry.offset + image.samplesOffset + pixel * image.bytesPerPixel
                    val existing = output.u16(absolute)
                    val replacement = SpriteTint.tintRgb565(existing, red, green, blue)
                    if (replacement == existing) return@repeat
                    val low = replacement.toByte()
                    val high = (replacement ushr 8).toByte()
                    if (output[absolute] != low) entryChanged++
                    if (output[absolute + 1] != high) entryChanged++
                    output[absolute] = low
                    output[absolute + 1] = high
                    // RGB565+A alpha byte, when present, remains verbatim.
                }
            }
            if (entryChanged > 0) {
                changed += entryChanged
                changedEntries += entry
            }
        }
        if (changed == 0) {
            throw Fit3FormatException("Sprite already uses that LCD tint")
        }
        return finalize(source, output, changedEntries, changed)
    }

    fun replaceBackgrounds(
''',
)

# 2) Repository contract.
replace(
    "core/model/src/main/kotlin/dev/fitface/studio/core/model/Models.kt",
    '''    suspend fun moveWidget(
''',
    '''    suspend fun recolorSpriteWidget(
        styleName: String,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        red: Int,
        green: Int,
        blue: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot

    suspend fun moveWidget(
''',
)

# 3) Repository implementation.
replace(
    "core/data/src/main/kotlin/dev/fitface/studio/core/data/WatchFaceRepositoryImpl.kt",
    '''    override suspend fun moveWidget(
''',
    '''    override suspend fun recolorSpriteWidget(
        styleName: String,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        red: Int,
        green: Int,
        blue: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot = withContext(Dispatchers.Default) {
        mutex.withLock {
            val current = requireSession()
            val styleNames = current.targetStyleNames(styleName, applyToAllStyles)
            val edit = FaceEditor.recolorSpriteWidgetAcrossStyles(
                source = current.currentContainer,
                entryBasenames = styleNames,
                globalIndex = globalIndex,
                sequenceId = sequenceId,
                x = x,
                y = y,
                red = red,
                green = green,
                blue = blue,
            )
            commit(
                current,
                edit.container,
                EditAuditSummary(
                    edit.changedPayloadBytes,
                    edit.changedStyles,
                    operation = if (applyToAllStyles) {
                        "Sprite LCD tint across all styles"
                    } else {
                        "Sprite LCD tint on selected style"
                    },
                ),
                styleName,
            )
        }
    }

    override suspend fun moveWidget(
''',
)

# 4) ViewModel action. C9/CE/CB is the approved cool LCD silver.
replace(
    "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt",
    '''    fun removeSelectedWidget() {
''',
    '''    fun setSelectedSpriteLcdSilver() {
        val snapshot = mutableState.value.snapshot ?: return
        val selected = snapshot.widgets.singleOrNull {
            it.globalIndex == mutableState.value.selectedWidgetIndex
        } ?: return
        if (selected.type != 3) return
        operate {
            repository.recolorSpriteWidget(
                styleName = snapshot.selectedStyle,
                globalIndex = selected.globalIndex,
                sequenceId = selected.sequenceId,
                x = selected.x,
                y = selected.y,
                red = 0xC9,
                green = 0xCE,
                blue = 0xCB,
                applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
            )
        }
    }

    fun removeSelectedWidget() {
''',
)

ui = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"

# 5) Route callback.
replace(
    ui,
    '''        onWidgetColor = viewModel::setSelectedWidgetColor,
        onSequenceStep = viewModel::stepSelectedWidgetSequence,
''',
    '''        onWidgetColor = viewModel::setSelectedWidgetColor,
        onSpriteLcdSilver = viewModel::setSelectedSpriteLcdSilver,
        onSequenceStep = viewModel::stepSelectedWidgetSequence,
''',
)

# 6) EditorScreen signature and forwarding.
replace(
    ui,
    '''    onWidgetColor: (Int) -> Unit,
    onSequenceStep: (Int) -> Unit,
''',
    '''    onWidgetColor: (Int) -> Unit,
    onSpriteLcdSilver: () -> Unit,
    onSequenceStep: (Int) -> Unit,
''',
)
replace(
    ui,
    '''                        onWidgetColor = onWidgetColor,
                        onSequenceStep = onSequenceStep,
''',
    '''                        onWidgetColor = onWidgetColor,
                        onSpriteLcdSilver = onSpriteLcdSilver,
                        onSequenceStep = onSequenceStep,
''',
)

# 7) EditorPageContent signature and Inspector call.
replace(
    ui,
    '''    onWidgetColor: (Int) -> Unit,
    onSequenceStep: (Int) -> Unit,
''',
    '''    onWidgetColor: (Int) -> Unit,
    onSpriteLcdSilver: () -> Unit,
    onSequenceStep: (Int) -> Unit,
''',
)
replace(
    ui,
    '''            onDuplicateWidget, onResizeWidget, onWidgetColor, onSequenceStep,
            onBindingStep, modifier,
''',
    '''            onDuplicateWidget, onResizeWidget, onWidgetColor, onSpriteLcdSilver,
            onSequenceStep, onBindingStep, modifier,
''',
)

# 8) Inspector signature.
replace(
    ui,
    '''    onColor: (Int) -> Unit,
    onSequenceStep: (Int) -> Unit,
''',
    '''    onColor: (Int) -> Unit,
    onSpriteLcdSilver: () -> Unit,
    onSequenceStep: (Int) -> Unit,
''',
)

# 9) Controls: exact silver for Sprite pool and Pair VALUE widgets.
replace(
    ui,
    '''        SpriteSizeControls(widget, !state.isWorking, onResize)
        if (widget.type == 5) {
''',
    '''        SpriteSizeControls(widget, !state.isWorking, onResize)
        if (widget.type == 3) {
            Column {
                MicroLabel("SPRITE COLOR · SHARED GLYPH POOL")
                FitButton(
                    text = "LCD Silver #C9CECB",
                    onClick = onSpriteLcdSilver,
                    modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                    enabled = !state.isWorking,
                    style = FitButtonStyle.Secondary,
                )
            }
        }
        if (widget.type == 5) {
''',
)
replace(
    ui,
    '''        widget.colorArgb?.let { currentColor ->
            val colors = listOf(
''',
    '''        widget.colorArgb?.let { currentColor ->
            FitButton(
                text = "LCD Silver #C9CECB",
                onClick = { onColor(0xFFC9_CECB.toInt()) },
                modifier = Modifier.fillMaxWidth(),
                enabled = !state.isWorking,
                style = FitButtonStyle.Secondary,
            )
            val colors = listOf(
''',
)

# 10) Distinguish this integrated build.
replace(
    "app/src/main/res/values/strings.xml",
    '<string name="app_name">FitFace Studio Bind Test</string>',
    '<string name="app_name">FitFace Studio LCD Test</string>',
)

print("LCD sprite/pair color patch applied")
