#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def replace(path: str, old: str, new: str) -> None:
    p = root / path
    text = p.read_text()
    count = text.count(old)
    # Some UI callback signatures intentionally occur more than once. Each patch call
    # consumes the first remaining occurrence, so only absence is an error.
    if count < 1:
        raise SystemExit(f"{path}: expected patch anchor, found {count}")
    p.write_text(text.replace(old, new, 1))

# 1) Format layer: change only the low byte of Pair words[1], which the independent
# parser identifies as the binding/font index. Alignment/layout bits in the upper bytes
# are preserved verbatim.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt",
    "    fun moveWidget(\n",
    '''    /** Experimental: changes only a type-5 Pair's binding index in words[1]. */
    fun overridePairBindingAcrossStyles(
        source: Fit3Container,
        entryBasenames: List<String>,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        newBindingIndex: Int,
    ): ContainerEdit {
        requireEditable(source)
        if (newBindingIndex !in 0..255) {
            throw Fit3FormatException("experimental Pair binding index must be in 0..255")
        }
        val targets = StyleWidgetMatch.resolve(source, entryBasenames) { _, records ->
            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == WIDGET_PAIR &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
        }
        targets.forEach { (_, record) ->
            if (record.words.size < 2) {
                throw Fit3FormatException("Pair widget has no binding/layout word")
            }
        }
        val output = source.toByteArray()
        val before = output.copyOf()
        targets.forEach { (entry, record) ->
            val bindingByte = entry.offset + record.recordOffset + WIDGET_FIXED_SIZE + 4
            output[bindingByte] = newBindingIndex.toByte()
        }
        var changed = 0
        targets.forEach { (entry, record) ->
            val bindingByte = entry.offset + record.recordOffset + WIDGET_FIXED_SIZE + 4
            if (before[bindingByte] != output[bindingByte]) changed++
        }
        if (changed == 0) {
            throw Fit3FormatException("Pair already uses binding index $newBindingIndex")
        }
        return finalize(source, output, targets.map { it.first }, changed)
    }

    fun moveWidget(
''',
)

# 2) Expose the current binding index in WidgetGuide and add repository API.
replace(
    "core/model/src/main/kotlin/dev/fitface/studio/core/model/Models.kt",
    '''    val colorArgb: Int?,
    val originalColorArgb: Int? = colorArgb,
''',
    '''    val colorArgb: Int?,
    /** Low byte of Pair words[1]; null for non-Pair or records without that word. */
    val pairBindingIndex: Int? = null,
    val originalColorArgb: Int? = colorArgb,
''',
)
replace(
    "core/model/src/main/kotlin/dev/fitface/studio/core/model/Models.kt",
    '''    suspend fun overrideWidgetSequence(
''',
    '''    suspend fun overridePairBinding(
        styleName: String,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        newBindingIndex: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot

    suspend fun overrideWidgetSequence(
''',
)

# 3) Decode Pair binding index into every editor snapshot.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt",
    '''            val pairColor = it.words.firstOrNull()?.takeIf { word ->
                word ushr 24 == 0xFFL
            }?.toInt()
            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
''',
    '''            val pairColor = it.words.firstOrNull()?.takeIf { word ->
                word ushr 24 == 0xFFL
            }?.toInt()
            val pairBindingIndex = if (it.widgetType == WIDGET_PAIR) {
                it.words.getOrNull(1)?.toInt()?.and(0xFF)
            } else {
                null
            }
            val canEditPair = it.widgetType == WIDGET_PAIR && pairMatches == 1 &&
''',
)
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceRecords.kt",
    '''                colorArgb = pairColor.takeIf { canEditPair },
                supportMessage = when {
''',
    '''                colorArgb = pairColor.takeIf { canEditPair },
                pairBindingIndex = pairBindingIndex,
                supportMessage = when {
''',
)

# 4) Repository implementation.
replace(
    "core/data/src/main/kotlin/dev/fitface/studio/core/data/WatchFaceRepositoryImpl.kt",
    '''    override suspend fun overrideWidgetSequence(
''',
    '''    override suspend fun overridePairBinding(
        styleName: String,
        globalIndex: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        newBindingIndex: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot = withContext(Dispatchers.Default) {
        mutex.withLock {
            val current = requireSession()
            val styleNames = current.targetStyleNames(styleName, applyToAllStyles)
            val edit = FaceEditor.overridePairBindingAcrossStyles(
                source = current.currentContainer,
                entryBasenames = styleNames,
                globalIndex = globalIndex,
                sequenceId = sequenceId,
                x = x,
                y = y,
                newBindingIndex = newBindingIndex,
            )
            commit(
                current,
                edit.container,
                EditAuditSummary(
                    edit.changedPayloadBytes,
                    edit.changedStyles,
                    operation = if (applyToAllStyles) {
                        "EXPERIMENTAL Pair binding override across styles -> $newBindingIndex"
                    } else {
                        "EXPERIMENTAL Pair binding override on selected style -> $newBindingIndex"
                    },
                ),
                styleName,
            )
        }
    }

    override suspend fun overrideWidgetSequence(
''',
)

# 5) ViewModel control.
replace(
    "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt",
    '''    fun stepSelectedWidgetSequence(delta: Int) {
''',
    '''    fun stepSelectedPairBinding(delta: Int) {
        val snapshot = mutableState.value.snapshot ?: return
        val selected = snapshot.widgets.singleOrNull {
            it.globalIndex == mutableState.value.selectedWidgetIndex
        } ?: return
        val current = selected.pairBindingIndex ?: return
        if (selected.type != 5 || delta == 0) return
        val next = (current + delta).coerceIn(0, 255)
        if (next == current) return
        operate {
            repository.overridePairBinding(
                styleName = snapshot.selectedStyle,
                globalIndex = selected.globalIndex,
                sequenceId = selected.sequenceId,
                x = selected.x,
                y = selected.y,
                newBindingIndex = next,
                applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
            )
        }
    }

    fun stepSelectedWidgetSequence(delta: Int) {
''',
)

# 6) UI callback plumbing, applied after the sequence-experiment patch.
ui = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"
replace(
    ui,
    '''        onSequenceStep = viewModel::stepSelectedWidgetSequence,
        onSyncThumbnail = viewModel::refreshThumbnail,
''',
    '''        onSequenceStep = viewModel::stepSelectedWidgetSequence,
        onBindingStep = viewModel::stepSelectedPairBinding,
        onSyncThumbnail = viewModel::refreshThumbnail,
''',
)
replace(
    ui,
    '''    onSequenceStep: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
    '''    onSequenceStep: (Int) -> Unit,
    onBindingStep: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
)
replace(
    ui,
    '''                        onSequenceStep = onSequenceStep,
                        onSyncThumbnail = onSyncThumbnail,
''',
    '''                        onSequenceStep = onSequenceStep,
                        onBindingStep = onBindingStep,
                        onSyncThumbnail = onSyncThumbnail,
''',
)
replace(
    ui,
    '''    onSequenceStep: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
    '''    onSequenceStep: (Int) -> Unit,
    onBindingStep: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
)
replace(
    ui,
    '''            onDuplicateWidget, onResizeWidget, onWidgetColor, onSequenceStep, modifier,
''',
    '''            onDuplicateWidget, onResizeWidget, onWidgetColor, onSequenceStep,
            onBindingStep, modifier,
''',
)
replace(
    ui,
    '''    onSequenceStep: (Int) -> Unit,
    modifier: Modifier = Modifier,
''',
    '''    onSequenceStep: (Int) -> Unit,
    onBindingStep: (Int) -> Unit,
    modifier: Modifier = Modifier,
''',
)
replace(
    ui,
    '''        if (widget.type == 5) {
            ExperimentalSequenceControls(
                widget = widget,
                enabled = !state.isWorking,
                onStep = onSequenceStep,
            )
        }
        widget.colorArgb?.let { currentColor ->
''',
    '''        if (widget.type == 5) {
            ExperimentalSequenceControls(
                widget = widget,
                enabled = !state.isWorking,
                onStep = onSequenceStep,
            )
            widget.pairBindingIndex?.let {
                ExperimentalPairBindingControls(
                    widget = widget,
                    enabled = !state.isWorking,
                    onStep = onBindingStep,
                )
            }
        }
        widget.colorArgb?.let { currentColor ->
''',
)
replace(
    ui,
    '''@Composable
private fun ExperimentalSequenceControls(
''',
    '''@Composable
private fun ExperimentalPairBindingControls(
    widget: WidgetGuide,
    enabled: Boolean,
    onStep: (Int) -> Unit,
) {
    val binding = widget.pairBindingIndex ?: return
    Column(
        Modifier.fillMaxWidth()
            .background(MaterialTheme.fitColors.warning.copy(alpha = .08f), MaterialTheme.shapes.small)
            .border(1.dp, MaterialTheme.fitColors.warning, MaterialTheme.shapes.small)
            .padding(14.dp),
    ) {
        MicroLabel("ADVANCED · PAIR BINDING TEST", color = MaterialTheme.fitColors.warning)
        Text(
            "Current binding $binding",
            modifier = Modifier.padding(top = 8.dp),
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            "Changes only the Pair binding/font index; sequence, position, alignment and " +
                "layout bits stay untouched. Unsupported indexes can render blank. " +
                "Keep Apply widget edits to every style OFF while testing.",
            modifier = Modifier.padding(top = 6.dp),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(
            Modifier.fillMaxWidth().padding(top = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            listOf(-10, -1, 1, 10).forEach { delta ->
                FitButton(
                    text = if (delta > 0) "+$delta" else delta.toString(),
                    onClick = { onStep(delta) },
                    modifier = Modifier.weight(1f),
                    enabled = enabled && (binding + delta) in 0..255,
                    style = FitButtonStyle.Secondary,
                )
            }
        }
    }
}

@Composable
private fun ExperimentalSequenceControls(
''',
)

# The sequence patch renamed the app; make this build visually distinct too.
replace(
    "app/src/main/res/values/strings.xml",
    '<string name="app_name">FitFace Studio Seq Test</string>',
    '<string name="app_name">FitFace Studio Bind Test</string>',
)

print("experimental Pair binding patch applied")
