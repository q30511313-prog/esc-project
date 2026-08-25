# Galaxy Fit3 SM-R390 single-shot color calibration

## Scope

Temporary hardware calibration only. The v10 branch `tmp-fitface-composite` remains untouched at commit `4779f94ae78ad29117975a0d8dd5fe34bac24f5a`.

Calibration branch: `tmp-fit3-color-calibration`

The calibration matrix is injected only when all of these are true:

- Samsung stock face `00003`
- `style3.bin` (black style)
- the proven foreground signature is present
- the selected logical color is `#B8B8AD`
- the clock Sprite recolor path is used

Normal faces, styles and colors do not receive the matrix.

## Purpose

One physical-device transfer replaces repeated one-color tests. Sixteen already-quantized RGB565 samples are displayed simultaneously on the Fit3 AMOLED panel.

- R5 is fixed at 22.
- G6 decreases from 47 to 44 left-to-right.
- B5 increases from 20 to 23 top-to-bottom.
- Patch 1 is the current v10 RGB565 payload `0xB5F4`.
- Patch 7 is the RGB565 quantization of logical `#B8B8AD`: `0xB5B5`.
- Patch 11 is approximately digitally neutral after RGB565 expansion: `0xB5B6`.

## Matrix

| | Column 1 | Column 2 | Column 3 | Column 4 |
|---|---:|---:|---:|---:|
| Row 1 | 1 `0xB5F4` | 2 `0xB5D4` | 3 `0xB5B4` | 4 `0xB594` |
| Row 2 | 5 `0xB5F5` | 6 `0xB5D5` | 7 `0xB5B5` | 8 `0xB595` |
| Row 3 | 9 `0xB5F6` | 10 `0xB5D6` | 11 `0xB5B6` | 12 `0xB596` |
| Row 4 | 13 `0xB5F7` | 14 `0xB5D7` | 15 `0xB5B7` | 16 `0xB597` |

Expanded nominal RGB values, before the Fit3 rendering/panel pipeline:

| Patch | RGB565 | Approx RGB888 |
|---:|---:|---:|
| 1 | `0xB5F4` | `(181,190,165)` |
| 2 | `0xB5D4` | `(181,186,165)` |
| 3 | `0xB5B4` | `(181,182,165)` |
| 4 | `0xB594` | `(181,178,165)` |
| 5 | `0xB5F5` | `(181,190,173)` |
| 6 | `0xB5D5` | `(181,186,173)` |
| 7 | `0xB5B5` | `(181,182,173)` |
| 8 | `0xB595` | `(181,178,173)` |
| 9 | `0xB5F6` | `(181,190,181)` |
| 10 | `0xB5D6` | `(181,186,181)` |
| 11 | `0xB5B6` | `(181,182,181)` |
| 12 | `0xB596` | `(181,178,181)` |
| 13 | `0xB5F7` | `(181,190,189)` |
| 14 | `0xB5D7` | `(181,186,189)` |
| 15 | `0xB5B7` | `(181,182,189)` |
| 16 | `0xB597` | `(181,178,189)` |

## Layout on the 256x402 screen

Four 40x40 patches per row.

- X starts: `24, 76, 128, 180`
- Y starts: `10, 110, 290, 340`

The central clock area is intentionally left available. The normal v10 foreground remains `#B8C0A1` / RGB565 `0xB5F4`, so patch 1 can also be compared directly against the clock elements to reveal any renderer-path difference.

## Physical test condition

For the calibration observation:

1. Disable Adaptive brightness on the Fit3.
2. Set the brightness slider to the midpoint and leave it fixed.
3. Load a fresh Samsung `00003` face.
4. Select black `style3`.
5. Select the clock SPRITE and apply logical `#B8B8AD` once.
6. Transfer to the Fit3 once.
7. Judge the 16 patches with the naked eye; do not use the phone camera as the final color reference.
8. Record the single patch number that is closest to the desired neutral G-SHOCK LCD tone.

No 16 separate transfers are required.

## Verification

TDD RED run: calibration test failed before implementation as expected.

GREEN build run: `32894289478`

- focused calibration + format regressions: PASS
- editor unit tests: PASS
- debug APK build: PASS
- APK artifact upload: PASS

Built APK SHA-256 after artifact extraction:

`c4005e363acaa56e10b43baa37440126c3a63270d8e558e2bfc1ef9ddf33d8e0`
