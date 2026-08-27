package dev.fitface.studio.core.format

/**
 * D2 style0 clean-plate + semantic/layout transaction for approved 1000028943 artwork.
 * Only style0 is rewritten; sibling style payloads and image record count are locked.
 */
object GoldenD2LayoutCompiler {
    const val WIDTH = 256
    const val HEIGHT = 402

    fun compile(source: Fit3Container): ContainerEdit = GoldenD2Compiler.compile(source)

    fun compile(
        source: Fit3Container,
        cleanPlateArgb: IntArray,
    ): ContainerEdit {
        if (cleanPlateArgb.size != WIDTH * HEIGHT) {
            throw Fit3FormatException("Golden D2 clean plate must be 256x402")
        }

        val siblings = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }
        val beforeStyle0 = source.entryByBasename("style0.bin")
        val beforeImages = FaceRecordParser.scanImages(beforeStyle0).size
        val beforeBackground = FaceRecordParser.backgroundImage(beforeStyle0)
            ?: throw Fit3FormatException("style0.bin: Golden D2 requires a panel background")
        if (beforeBackground.width != WIDTH || beforeBackground.height != HEIGHT) {
            throw Fit3FormatException("style0.bin: Golden D2 background must be 256x402")
        }

        val backgroundEdit = FaceEditor.replaceBackgroundInStyle(
            source = source,
            entryBasename = "style0.bin",
            width = WIDTH,
            height = HEIGHT,
            argb = cleanPlateArgb,
        )
        val semanticEdit = GoldenD2Compiler.compile(backgroundEdit.container)
        val output = semanticEdit.container

        siblings.forEach { (name, bytes) ->
            if (!bytes.contentEquals(output.entryByBasename(name).data)) {
                throw Fit3FormatException("Golden D2 modified sibling $name")
            }
        }
        val afterStyle0 = output.entryByBasename("style0.bin")
        if (FaceRecordParser.scanImages(afterStyle0).size != beforeImages) {
            throw Fit3FormatException("Golden D2 changed style0 image record count")
        }
        val afterBackground = FaceRecordParser.backgroundImage(afterStyle0)
            ?: throw Fit3FormatException("style0.bin: Golden D2 lost its panel background")
        if (afterBackground.width != WIDTH || afterBackground.height != HEIGHT) {
            throw Fit3FormatException("style0.bin: Golden D2 background geometry drifted")
        }

        val report = output.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden D2 layout failed validation: " + report.errors.joinToString { it.code },
            )
        }
        val changed = backgroundEdit.changedPayloadBytes + semanticEdit.changedPayloadBytes
        if (changed <= 0) {
            throw Fit3FormatException("Golden D2 layout would not change any bytes")
        }
        return ContainerEdit(
            container = output,
            changedPayloadBytes = changed,
            changedStyles = listOf("style0.bin"),
        )
    }
}
