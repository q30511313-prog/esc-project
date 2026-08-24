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

# Static/type-1 widgets point directly at one raster via +0x20. Repaint that exact
# raster in place, preserving dimensions, format, alpha bytes, trailer and all pointers.
replace(
    "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt",
    '''    fun replaceBackgrounds(
''',
    '''    fun recolorStaticWidgetAcrossStyles(
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
                    it.widgetType == WIDGET_STATIC &&
                    it.sequenceId == sequenceId &&
                    it.x == x &&
                    it.y == y
            }
        }
        val output = source.toByteArray()
        var changed = 0
        val changedEntries = mutableListOf<ContainerEntry>()
        targets.forEach { (entry, target) ->
            val images = FaceRecordParser.scanImages(entry)
            val firstImageOffset = images.firstOrNull()?.recordOffset
                ?: throw Fit3FormatException("${entry.basename}: Static has no image pool")
            val imagesByRelativeOffset = images.associateBy {
                (it.recordOffset - firstImageOffset).toLong()
            }
            val image = imagesByRelativeOffset[target.unknown20]
                ?: throw Fit3FormatException(
                    "${entry.basename}: Static +0x20 does not point at a raster",
                )
            val background = FaceRecordParser.backgroundImage(entry)
            if (background?.recordOffset == image.recordOffset) {
                throw Fit3FormatException("${entry.basename}: refusing to tint the panel background as a widget")
            }
            if (image.format !in setOf(IMAGE_RGB565, IMAGE_RGB565_ALPHA)) {
                throw Fit3FormatException(
                    "${entry.basename}: LCD tint supports RGB565 and RGB565+A Static rasters only",
                )
            }
            var entryChanged = 0
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
                // RGB565+A alpha byte stays byte-identical.
            }
            if (entryChanged > 0) {
                changed += entryChanged
                changedEntries += entry
            }
        }
        if (changed == 0) {
            throw Fit3FormatException("Static raster already uses that LCD tint")
        }
        return finalize(source, output, changedEntries, changed)
    }

    fun replaceBackgrounds(
''',
)

replace(
    "core/model/src/main/kotlin/dev/fitface/studio/core/model/Models.kt",
    '''    suspend fun moveWidget(
''',
    '''    suspend fun recolorStaticWidget(
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

replace(
    "core/data/src/main/kotlin/dev/fitface/studio/core/data/WatchFaceRepositoryImpl.kt",
    '''    override suspend fun moveWidget(
''',
    '''    override suspend fun recolorStaticWidget(
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
            val edit = FaceEditor.recolorStaticWidgetAcrossStyles(
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
                        "Static raster LCD tint across compatible styles"
                    } else {
                        "Static raster LCD tint on selected style"
                    },
                ),
                styleName,
            )
        }
    }

    override suspend fun moveWidget(
''',
)

# Reuse the already-hardware-proven Sprite button callback. It now dispatches to
# Static or Sprite without changing the Sprite implementation at all.
vm = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorViewModel.kt"
replace(
    vm,
    '''        if (selected.type != 3) return
        operate {
            repository.recolorSpriteWidget(
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
    '''        if (selected.type !in setOf(1, 3)) return
        operate {
            when (selected.type) {
                1 -> repository.recolorStaticWidget(
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
                3 -> repository.recolorSpriteWidget(
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
        }
''',
)

ui = "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/EditorScreen.kt"
replace(
    ui,
    '''        if (widget.type == 3) {
            Column {
                MicroLabel("SPRITE COLOR · SHARED GLYPH POOL")
''',
    '''        if (widget.type == 1 || widget.type == 3) {
            Column {
                MicroLabel(
                    if (widget.type == 1) "IMAGE COLOR · RASTER PIXELS"
                    else "SPRITE COLOR · SHARED GLYPH POOL",
                )
''',
)

print("Static/type-1 raster LCD tint patch applied")
