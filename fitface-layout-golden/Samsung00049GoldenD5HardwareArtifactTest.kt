package dev.fitface.studio.core.format

import java.nio.file.Files
import java.nio.file.Path
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Samsung00049GoldenD5HardwareArtifactTest {
    @Test
    fun writesValidatedHardwarePayload() {
        val outputDir = System.getenv("D5_HARDWARE_ARTIFACT_DIR")
            ?: throw AssertionError("D5_HARDWARE_ARTIFACT_DIR must be set")
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/fixtures/SM-R390_00049_256x402.bin"),
        ) { "real Samsung 00049 fixture must be staged by CI" }
        val pristine = Fit3Container.parse(stream.readBytes())
        assertTrue(pristine.validate().isValid)

        val hardware = GoldenD5HardwareBaseline.resolve("00049", pristine)
        assertTrue(hardware.validate().isValid)
        assertTrue(hardware.fileSize < 4 * 1024 * 1024)

        val bytes = hardware.toByteArray()
        val reparsed = Fit3Container.parse(bytes)
        assertTrue(reparsed.validate().isValid)
        assertArrayEquals(bytes, reparsed.toByteArray())

        val dir = Path.of(outputDir)
        Files.createDirectories(dir)
        Files.write(dir.resolve("SM-R390_00049_D5_hardware.bin"), bytes)
    }
}
