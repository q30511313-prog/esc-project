package dev.fitface.studio.core.format

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049AmPmLocaleExtensionTest {
    @Test
    fun compileAmPmExtendsKoreanLocaleAndBindsSeq5ToTheNewGroupPair() {
        val source = real00049()
        val beforeLocale = parseLocale(source.entryByBasename("font_ko.bin").data)
        assertEquals(12, beforeLocale.size)
        assertTrue(beforeLocale.none { it.decodeToString() in setOf("오전", "오후") })
        val beforeFont1 = source.entryByBasename("font_1.bin").data.copyOf()
        assertEquals("WF_BMP", fontRole(beforeFont1))
        assertEquals(20, beforeFont1.u32(0x58).toInt())

        val untouchedStyles = listOf("style1.bin", "style2.bin", "style3.bin")
            .associateWith { source.entryByBasename(it).data.copyOf() }
        val pristineDonor = FaceRecordParser.scanWidgets(source.entryByBasename("style0.bin"))
            .single { it.globalIndex == 9 && it.widgetType == WIDGET_PAIR && it.sequenceId == 41 }
        assertEquals(0x0001FFFFL, pristineDonor.words[2])

        val edit = GoldenSemanticCompiler.compileAmPm(
            source = source,
            entryBasename = "style0.bin",
            x = 48,
            y = 120,
        )

        val edited = edit.container
        val afterLocale = parseLocale(edited.entryByBasename("font_ko.bin").data)
        assertEquals("Golden AM/PM locale must append exactly two groups", 14, afterLocale.size)
        beforeLocale.indices.forEach { index ->
            assertArrayEquals(beforeLocale[index], afterLocale[index])
        }
        assertEquals("오전", afterLocale[12].decodeToString())
        assertEquals("오후", afterLocale[13].decodeToString())

        val afterFont1 = edited.entryByBasename("font_1.bin").data
        assertEquals(92, afterFont1.size)
        assertEquals("WF_AM_PM", fontRole(afterFont1))
        // Keep 00049's compact 20px binding rather than copying a larger stock face.
        assertEquals(20, afterFont1.u32(0x58).toInt())

        val amPm = FaceRecordParser.scanWidgets(edited.entryByBasename("style0.bin"))
            .single { it.globalIndex == 9 && it.widgetType == WIDGET_PAIR && it.sequenceId == 5 }
        assertEquals(48, amPm.x)
        assertEquals(120, amPm.y)
        assertEquals(1, amPm.words[1].toInt() and 0xFF)
        assertEquals(
            pristineDonor.words[1] and 0xFFFF_FF00L,
            amPm.words[1] and 0xFFFF_FF00L,
        )
        assertEquals(0x0001000CL, amPm.words[2])

        untouchedStyles.forEach { (name, bytes) ->
            assertArrayEquals(bytes, edited.entryByBasename(name).data)
        }
        assertEquals(source.fileSize + 28, edited.fileSize)
        assertTrue(edited.validate().isValid)
    }

    private fun parseLocale(data: ByteArray): List<ByteArray> {
        assertEquals(0x12345678L, data.u32(0))
        val count = data.u32(8).toInt()
        val descriptorEnd = 0x18 + count * 8
        assertTrue(descriptorEnd <= data.size)
        return List(count) { index ->
            val descriptor = 0x18 + index * 8
            val length = data.u32(descriptor).toInt()
            val offset = data.u32(descriptor + 4).toInt()
            assertTrue(offset >= descriptorEnd)
            assertTrue(offset + length <= data.size)
            data.copyOfRange(offset, offset + length)
        }
    }

    private fun fontRole(data: ByteArray): String {
        val raw = data.copyOfRange(0x48, 0x58)
        val end = raw.indexOf(0).let { if (it < 0) raw.size else it }
        return String(raw, 0, end, StandardCharsets.US_ASCII)
    }

    private fun real00049(): Fit3Container {
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        return Fit3Container.parse(stream.readBytes()).also {
            assertTrue(it.validate().isValid)
        }
    }
}
