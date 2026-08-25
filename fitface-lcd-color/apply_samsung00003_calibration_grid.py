#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
path = root / "core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt"
text = path.read_text()

old = '''            // style3 background is RGB565+A; alpha is deliberately untouched.
        }
        return changed
    }

    fun replaceBackgrounds(
'''

new = '''            // style3 background is RGB565+A; alpha is deliberately untouched.
        }

        // Temporary single-shot hardware calibration matrix. This is deliberately
        // gated by the same Samsung 00003/style3/#B8B8AD optical-calibration path
        // as v10, so normal faces and normal colors remain byte-identical.
        //
        // Each square is written as an already-quantized RGB565 code. R5 is held
        // at 22 while G6 steps 47 -> 44 across columns and B5 steps 20 -> 23 down
        // rows. That isolates the green/magenta and yellow/blue axes that moved
        // between the v9 and v10 physical-screen observations without wasting
        // transfers on RGB888 values that collapse to the same RGB565 code.
        if (useFit3OpticalCalibration) {
            val calibrationColors = intArrayOf(
                0xB5F4, 0xB5D4, 0xB5B4, 0xB594,
                0xB5F5, 0xB5D5, 0xB5B5, 0xB595,
                0xB5F6, 0xB5D6, 0xB5B6, 0xB596,
                0xB5F7, 0xB5D7, 0xB5B7, 0xB597,
            )
            val patchXs = intArrayOf(24, 76, 128, 180)
            val patchYs = intArrayOf(10, 110, 290, 340)
            val patchSize = 40

            calibrationColors.forEachIndexed { index, candidate ->
                val startX = patchXs[index % 4]
                val startY = patchYs[index / 4]
                for (patchY in startY until startY + patchSize) {
                    for (patchX in startX until startX + patchSize) {
                        val pixel = patchY * background.width + patchX
                        val absolute = entry.offset + background.samplesOffset +
                            pixel * background.bytesPerPixel
                        writeRgb565(absolute, candidate)
                        if (
                            background.format == IMAGE_RGB565_ALPHA &&
                            output[absolute + 2] != 0xFF.toByte()
                        ) {
                            output[absolute + 2] = 0xFF.toByte()
                            changed++
                        }
                    }
                }
            }
        }
        return changed
    }

    fun replaceBackgrounds(
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"FaceEditor.kt: expected one Samsung 00003 chrome tail, found {count}")

path.write_text(text.replace(old, new, 1))
print("Samsung 00003 style3 single-shot 16-patch RGB565 calibration matrix applied")
