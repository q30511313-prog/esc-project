package dev.fitface.studio.core.format

/**
 * Places Samsung 00049's native 24-frame weather Sprite inside the D1 weather box.
 *
 * The 30x30 weather pool is intentionally left byte-identical. The surrounding
 * circle/frame belongs to the static clean plate, so stretching the live icon would
 * only add raster risk without adding information.
 */
fun GoldenSemanticCompiler.compileWeatherIcon(
    source: Fit3Container,
    entryBasename: String,
    x: Int,
    y: Int,
): ContainerEdit {
    if (entryBasename != "style0.bin") {
        throw Fit3FormatException(
            "Golden weather icon contract is defined only for style0.bin",
        )
    }

    val record = FaceRecordParser.scanWidgets(
        source.entryByBasename(entryBasename),
    ).singleOrNull {
        it.globalIndex == 7 &&
            it.widgetType == WIDGET_SPRITE &&
            it.sequenceId == 69 &&
            it.x == 180 &&
            it.y == 102 &&
            it.words.size == 24
    } ?: throw Fit3FormatException(
        "Golden weather icon Sprite g7/seq69@(180,102) with 24 frames is missing or ambiguous",
    )

    val entry = source.entryByBasename(entryBasename)
    val images = FaceRecordParser.scanImages(entry)
    val firstImageOffset = images.firstOrNull()?.recordOffset
        ?: throw Fit3FormatException("Golden weather icon style has no image section")
    val byRelative = images.associateBy { (it.recordOffset - firstImageOffset).toLong() }
    val frames = record.words.map { pointer ->
        byRelative[pointer] ?: throw Fit3FormatException(
            "Golden weather icon pointer $pointer does not resolve to an image",
        )
    }
    if (frames.distinctBy { it.index }.size != 24 || frames.any {
            it.width != 30 ||
                it.height != 30 ||
                it.format != IMAGE_RGB565_ALPHA ||
                it.reserved != 0 ||
                it.opaqueTrailerSize != 4
        }
    ) {
        throw Fit3FormatException(
            "Golden weather icon pool must remain the pristine 24x 30x30 RGB565+A schema",
        )
    }

    return FaceEditor.moveWidget(
        source = source,
        entryBasename = entryBasename,
        globalIndex = 7,
        widgetType = WIDGET_SPRITE,
        sequenceId = 69,
        x = x,
        y = y,
    )
}
