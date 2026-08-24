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

# 1) Format layer: same-size sequence-id rewrite, deliberately limited to type-5 VALUE.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt",
    "object FaceEditor {\n    fun moveWidget(\n",
    '''object FaceEditor {
    /**
     * Experimental: rebinds an existing type-5 VALUE widget to another firmware
     * sequence id. This does not create a new data source; it only tests whether a
     * sequence the firmware already publishes is meaningful for this VALUE schema.
     *
     * The rewrite is intentionally same-size and VALUE-only. Raster-backed Sprite
     * records carry sequence-specific frame tables and must never be rebound this way.
     */
    fun overrideWidgetSequenceAcrossStyles(
        source: Fit3Container,
        entryBasenames: List<String>,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        newSequenceId: Int,
    ): ContainerEdit {
        requireEditable(source)
        if (widgetType != WIDGET_PAIR) {
            throw Fit3FormatException(
                "experimental sequence override is limited to type-5 VALUE widgets",
            )
        }
        if (newSequenceId !in 0..255) {
            throw Fit3FormatException("experimental sequence id must be in 0..255")
        }
        if (newSequenceId == sequenceId) {
            throw Fit3FormatException("widget already uses sequence $newSequenceId")
        }
        val targets = StyleWidgetMatch.resolve(source, entryBasenames) { _, records ->
            records.singleOrNull {
                it.globalIndex == globalIndex &&
                    it.widgetType == widgetType &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
        }
        val output = source.toByteArray()
        val before = output.copyOf()
        targets.forEach { (entry, record) ->
            output.putU32(
                entry.offset + record.recordOffset + 0x04,
                newSequenceId,
            )
        }
        var changed = 0
        targets.forEach { (entry, record) ->
            val start = entry.offset + record.recordOffset + 0x04
            changed += (start until start + 4).count { before[it] != output[it] }
        }
        if (changed == 0) {
            throw Fit3FormatException("sequence override would not change any bytes")
        }
        return finalize(source, output, targets.map { it.first }, changed)
    }

    fun moveWidget(
''',
)

# 2) Repository API.
replace(
    "core/model/src/main/kotlin/dev/fitface/studio/core/model/Models.kt",
    '''    suspend fun moveWidget(
        styleName: String,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot
''',
    '''    suspend fun overrideWidgetSequence(
        styleName: String,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        newSequenceId: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot

    suspend fun moveWidget(
        styleName: String,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot
''',
)

# 3) Repository implementation. Keep the hardware experiment style-scoped when the
# user disables the existing "apply to all styles" switch.
replace(
    "core/data/src/main/kotlin/dev/fitface/studio/core/data/WatchFaceRepositoryImpl.kt",
    '''    override suspend fun moveWidget(
        styleName: String,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot = withContext(Dispatchers.Default) {
''',
    '''    override suspend fun overrideWidgetSequence(
        styleName: String,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        newSequenceId: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot = withContext(Dispatchers.Default) {
        mutex.withLock {
            val current = requireSession()
            val styleNames = current.targetStyleNames(styleName, applyToAllStyles)
            val edit = FaceEditor.overrideWidgetSequenceAcrossStyles(
                source = current.currentContainer,
                entryBasenames = styleNames,
                globalIndex = globalIndex,
                widgetType = widgetType,
                sequenceId = sequenceId,
                x = x,
                y = y,
                newSequenceId = newSequenceId,
            )
            commit(
                current,
                edit.container,
                EditAuditSummary(
                    edit.changedPayloadBytes,
                    edit.changedStyles,
                    operation = if (applyToAllStyles) {
                        "EXPERIMENTAL VALUE sequence override across styles: $sequenceId -> $newSequenceId"
                    } else {
                        "EXPERIMENTAL VALUE sequence override on selected style: $sequenceId -> $newSequenceId"
                    },
                ),
                styleName,
            )
        }
    }

    override suspend fun moveWidget(
        styleName: String,
        globalIndex: Int,
        widgetType: Int,
        sequenceId: Int,
        x: Int,
        y: Int,
        applyToAllStyles: Boolean,
    ): EditorSnapshot = withContext(Dispatchers.Default) {
''',
)

# 4) ViewModel action. Delta controls keep the experiment generic while making seq 14/15
# reachable quickly from common VALUE sequences.
replace(
    "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt",
    '''    fun removeSelectedWidget() {
''',
    '''    fun stepSelectedWidgetSequence(delta: Int) {
        val snapshot = mutableState.value.snapshot ?: return
        val selected = snapshot.widgets.singleOrNull {
            it.globalIndex == mutableState.value.selectedWidgetIndex
        } ?: return
        if (selected.type != 5 || delta == 0) return
        val next = (selected.sequenceId + delta).coerceIn(0, 255)
        if (next == selected.sequenceId) return
        operate {
            repository.overrideWidgetSequence(
                styleName = snapshot.selectedStyle,
                globalIndex = selected.globalIndex,
                widgetType = selected.type,
                sequenceId = selected.sequenceId,
                x = selected.x,
                y = selected.y,
                newSequenceId = next,
                applyToAllStyles = mutableState.value.applyWidgetEditsToAllStyles,
            )
        }
    }

    fun removeSelectedWidget() {
''',
)

# 5) UI callback plumbing.
ui = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"
replace(
    ui,
    '''        onWidgetColor = viewModel::setSelectedWidgetColor,
        onSyncThumbnail = viewModel::refreshThumbnail,
''',
    '''        onWidgetColor = viewModel::setSelectedWidgetColor,
        onSequenceStep = viewModel::stepSelectedWidgetSequence,
        onSyncThumbnail = viewModel::refreshThumbnail,
''',
)
replace(
    ui,
    '''    onResizeWidget: (Boolean) -> Unit,
    onWidgetColor: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
    '''    onResizeWidget: (Boolean) -> Unit,
    onWidgetColor: (Int) -> Unit,
    onSequenceStep: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
)
replace(
    ui,
    '''                        onResizeWidget = onResizeWidget,
                        onWidgetColor = onWidgetColor,
                        onSyncThumbnail = onSyncThumbnail,
''',
    '''                        onResizeWidget = onResizeWidget,
                        onWidgetColor = onWidgetColor,
                        onSequenceStep = onSequenceStep,
                        onSyncThumbnail = onSyncThumbnail,
''',
)
replace(
    ui,
    '''    onResizeWidget: (Boolean) -> Unit,
    onWidgetColor: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
    '''    onResizeWidget: (Boolean) -> Unit,
    onWidgetColor: (Int) -> Unit,
    onSequenceStep: (Int) -> Unit,
    onSyncThumbnail: () -> Unit,
''',
)
replace(
    ui,
    '''            onDuplicateWidget, onResizeWidget, onWidgetColor, modifier,
''',
    '''            onDuplicateWidget, onResizeWidget, onWidgetColor, onSequenceStep, modifier,
''',
)
replace(
    ui,
    '''    onResize: (Boolean) -> Unit,
    onColor: (Int) -> Unit,
    modifier: Modifier = Modifier,
''',
    '''    onResize: (Boolean) -> Unit,
    onColor: (Int) -> Unit,
    onSequenceStep: (Int) -> Unit,
    modifier: Modifier = Modifier,
''',
)
replace(
    ui,
    '''        SpriteSizeControls(widget, !state.isWorking, onResize)
        widget.colorArgb?.let { currentColor ->
''',
    '''        SpriteSizeControls(widget, !state.isWorking, onResize)
        if (widget.type == 5) {
            ExperimentalSequenceControls(
                widget = widget,
                enabled = !state.isWorking,
                onStep = onSequenceStep,
            )
        }
        widget.colorArgb?.let { currentColor ->
''',
)
replace(
    ui,
    '''@Composable
private fun CoordinateControl(
''',
    '''@Composable
private fun ExperimentalSequenceControls(
    widget: WidgetGuide,
    enabled: Boolean,
    onStep: (Int) -> Unit,
) {
    Column(
        Modifier.fillMaxWidth()
            .background(MaterialTheme.fitColors.warning.copy(alpha = .08f), MaterialTheme.shapes.small)
            .border(1.dp, MaterialTheme.fitColors.warning, MaterialTheme.shapes.small)
            .padding(14.dp),
    ) {
        MicroLabel("ADVANCED · SEQUENCE TEST", color = MaterialTheme.fitColors.warning)
        Text(
            "Current seq ${widget.sequenceId}",
            modifier = Modifier.padding(top = 8.dp),
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            "Experimental firmware data-source rebind for type-5 VALUE only. " +
                "Unsupported sequences may render blank or wrong on the watch. " +
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
                    enabled = enabled && (widget.sequenceId + delta) in 0..255,
                    style = FitButtonStyle.Secondary,
                )
            }
        }
    }
}

@Composable
private fun CoordinateControl(
''',
)

# 6) Distinguish this debug build on the phone.
replace(
    "app/src/main/res/values/strings.xml",
    '<string name="app_name">FitFace Studio</string>',
    '<string name="app_name">FitFace Studio Seq Test</string>',
)

print("experimental sequence override patch applied")
