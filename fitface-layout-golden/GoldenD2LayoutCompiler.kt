package dev.fitface.studio.core.format

/**
 * D2 style0 semantic/layout transaction. The D2 artwork background is installed by
 * the dedicated clean-plate stage; this compiler owns only the live-widget geometry.
 */
object GoldenD2LayoutCompiler {
    fun compile(source: Fit3Container): ContainerEdit {
        val siblings = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }
        val edit = GoldenD2Compiler.compile(source)
        siblings.forEach { (name, bytes) ->
            if (!bytes.contentEquals(edit.container.entryByBasename(name).data)) {
                throw Fit3FormatException("Golden D2 modified sibling $name")
            }
        }
        val report = edit.container.validate()
        if (!report.isValid) {
            throw Fit3FormatException(
                "Golden D2 layout failed validation: " + report.errors.joinToString { it.code },
            )
        }
        return edit
    }
}
