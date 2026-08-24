package dev.fitface.studio.core.format

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class OpaqueRgb565ResizeTest {
    @Test
    fun nearestOpaqueRgb565KeepsTwoBytesPerPixel() {
        // 2x2 RGB565 pixels, each intentionally distinct.
        val source = byteArrayOf(
            0x00, 0x00,
            0x11, 0x22,
            0x33, 0x44,
            0x55, 0x66,
        )
        val resized = StructuralEditor.nearestRgb565Opaque(
            source = source,
            oldWidth = 2,
            oldHeight = 2,
            newWidth = 1,
            newHeight = 2,
        )
        assertEquals(4, resized.size)
        // Nearest-neighbour takes x=0 from each source row.
        assertArrayEquals(byteArrayOf(0x00, 0x00, 0x33, 0x44), resized)
    }

    @Test(expected = Fit3FormatException::class)
    fun nearestOpaqueRgb565RejectsWrongPayloadLength() {
        StructuralEditor.nearestRgb565Opaque(
            source = byteArrayOf(0x00, 0x00, 0x00),
            oldWidth = 1,
            oldHeight = 1,
            newWidth = 1,
            newHeight = 1,
        )
    }
}
