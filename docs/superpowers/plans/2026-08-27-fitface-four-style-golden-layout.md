# FitFace Four-Style Golden Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one Samsung Fit3 watch-face package with four style slots, first proving design 1 as a hardware-testable Golden Layout on `style0` with live date, weekday, Korean AM/PM, HH:MM, seconds, battery, weather state/text, and temperature while preserving the approved LCD colour calibration.

**Architecture:** Start from Samsung `00049 Detailed dashboard`, because it already carries weekday, date, weather, temperature, battery and HH:MM resources. Add only bounded, fail-closed semantic remaps and style-scoped layout operations to the existing FitFace format engine; use `style0` as the Golden proof and leave `style1`–`style3` structurally untouched until hardware validation passes. The existing v12 Foundation/v11 patch stack remains the base and the approved optical colour pass runs last.

**Tech Stack:** Kotlin/JVM, FitFace `core:format`, Python 3 patch/build helpers, JSON layout recipes, GitHub Actions, Gradle/JDK 17, Android debug APK, Samsung Fit3 SM-R390 binary container.

**Spec:** `docs/FITFACE_LAYOUT_PRODUCTION_ARCHITECTURE.md`

## Global Constraints

- Packaging is fixed: one face with `style0 = design 1`, `style1 = design 2`, `style2 = design 3`, `style3 = design 4`.
- Golden implementation changes only `style0`; `style1`–`style3` are expanded only after real-watch approval.
- Base stock face is Samsung `00049 Detailed dashboard`.
- Upstream remains `satvikgosai/fitface-studio@45a9788d3877627fd5301e9ebba36ef6192d7962`.
- Preserve the v12 Foundation/v11 production patch stack and its validation behavior.
- Logical/UI colour stays `#B8B8AD`.
- Fit3 optical payload stays `#B5B6BD`, RGB565 `0xB5B7`.
- Never append a new Sprite image-frame inventory for the Golden proof; image record counts must remain stable.
- Every semantic mutation must identify the source record by type + original sequence + original identity/position and fail closed on zero or multiple matches.
- Every build reparses the resulting container, rebuilds CRCs, checks round-trip validity and enforces the existing 4 MiB watch-face limit.
- Static punctuation/decorations (`:`, `/`, `년`, `월`, `일`, battery outline) belong in the clean plate where possible.
- No automatic image generation or generative image editing is part of this implementation.

---

### Task 1: Golden branch and real 00049 semantic fixture contract

**Files:**
- Create: `fitface-layout-golden/Samsung00049SemanticInventoryTest.kt`
- Create: `fitface-layout-golden/fetch_face00049_fixture.py`
- Create: `.github/workflows/build-fitface-four-style-golden.yml` (RED fixture/inventory phase)

**Interfaces:**
- Consumes: Samsung Store public Fit3 package endpoint and `SM-R390_00049_256x402.bin`.
- Produces: a real `00049` fixture copied at CI runtime to `core/format/src/test/resources/fixtures/SM-R390_00049_256x402.bin` plus a regression test locking the exact style0 semantic records needed by later tasks.

- [ ] **Step 1: Write the failing semantic inventory test**

The test must load the runtime fixture and assert that `style0.bin` contains exactly the expected identities before any remap:

```kotlin
val records = FaceRecordParser.scanWidgets(style0)
fun one(type: Int, sequence: Int) = records.single {
    it.widgetType == type && it.sequenceId == sequence
}
assertEquals(17, one(WIDGET_PAIR, 17).sequenceId)   // weekday
assertEquals(2, one(WIDGET_SPRITE, 2).sequenceId)   // hour tens
assertEquals(3, one(WIDGET_SPRITE, 3).sequenceId)   // hour ones
assertEquals(10, one(WIDGET_SPRITE, 10).sequenceId) // minute tens
assertEquals(11, one(WIDGET_SPRITE, 11).sequenceId) // minute ones
assertEquals(69, one(WIDGET_SPRITE, 69).sequenceId) // weather
assertEquals(37, one(WIDGET_BADGE, 37).sequenceId)  // battery gauge
```

The same test must assert that the donor Pair sequences 41, 29, 48 and 115 exist once each and that the source container validates before editing.

- [ ] **Step 2: Add the fixture downloader**

`fetch_face00049_fixture.py` must reproduce the already-verified Samsung request shape, use a fixed non-sensitive Android-ID-shaped `extuk`, require `resultCode=1`, require exactly one `SM-R390_00049_256x402.bin`, enforce HTTPS/trusted Samsung host, and write only that container to the caller-supplied output path.

- [ ] **Step 3: Run RED before the fixture is staged**

Run in CI after cloning upstream and before calling the fixture downloader:

```bash
./gradlew --no-daemon :core:format:testDebugUnitTest \
  --tests dev.fitface.studio.core.format.Samsung00049SemanticInventoryTest
```

Expected: FAIL because the real fixture is absent.

- [ ] **Step 4: Stage the fixture and rerun GREEN**

Run:

```bash
python3 helper/fitface-layout-golden/fetch_face00049_fixture.py \
  fitface-studio/core/format/src/test/resources/fixtures/SM-R390_00049_256x402.bin
./gradlew --no-daemon :core:format:testDebugUnitTest \
  --tests dev.fitface.studio.core.format.Samsung00049SemanticInventoryTest
```

Expected: PASS and container validation success.

- [ ] **Step 5: Commit fixture contract**

Commit message:

```text
test: lock Samsung 00049 Golden semantic inventory
```

---

### Task 2: Fail-closed style-scoped Pair semantic remap primitive

**Files:**
- Create: `fitface-layout-golden/Samsung00049PairSequenceRemapTest.kt`
- Create: `fitface-layout-golden/apply_golden_format_patch.py`
- Modify at build time through patch: `core/format/src/main/kotlin/dev/fitface/studio/core/format/FaceEditor.kt`

**Interfaces:**
- Consumes: existing `Fit3Container`, `StyleWidgetMatch.resolve`, Pair donor identity.
- Produces:

```kotlin
FaceEditor.remapPairSequence(
    source: Fit3Container,
    entryBasename: String,
    originalSequenceId: Int,
    x: Int,
    y: Int,
    newSequenceId: Int,
): ContainerEdit
```

- [ ] **Step 1: Write tests before the mutator exists**

Test cases must prove:

```kotlin
// style0 donor changes from 41 -> 14
// style1/style2/style3 bytes stay identical
// only the four bytes at record + 0x04 change before CRC rebuild
// zero match throws Fit3FormatException
// duplicate match throws Fit3FormatException
// non-Pair target throws
// newSequenceId outside 0..255 throws
// same old/new sequence throws
```

- [ ] **Step 2: Run RED**

Expected: compile failure because `remapPairSequence` does not yet exist.

- [ ] **Step 3: Implement minimal same-size Pair-only remap**

The mutator must resolve exactly one record from exactly one named style, patch only the sequence word, then reuse existing `finalize(...)` CRC/validation logic. It must not expose an all-styles switch.

- [ ] **Step 4: Run focused GREEN**

Run inventory + remap tests and existing Pair/Sequence regressions.

- [ ] **Step 5: Commit**

```text
feat: add style-scoped Golden Pair sequence remap
```

---

### Task 3: Prove small live seconds on Pair sources 14/15

**Files:**
- Create: `fitface-layout-golden/Samsung00049SecondsCompilerTest.kt`
- Extend: `fitface-layout-golden/apply_golden_format_patch.py`
- Create: `fitface-layout-golden/golden_layout_recipe.json`

**Interfaces:**
- Consumes: donor Pair seq 41 and 29 from pristine `00049/style0`.
- Produces: a `SecondsCompiler`/helper operation that remaps the two donors to 14 and 15, assigns an independent numeric binding, and positions them inside design-1 `SECONDS = (48,257,47,30)`.

- [ ] **Step 1: Define Golden recipe contract**

`golden_layout_recipe.json` must copy design 1 boxes exactly from `fitface-layout/layout_recipes_v1.json` and include immutable semantic IDs:

```json
{
  "style": "style0.bin",
  "seconds": {"tens": 14, "ones": 15},
  "am_pm": 5,
  "weekday": 17,
  "year": 24,
  "month": 21,
  "day": 18,
  "temperature": 62,
  "weather": 69,
  "battery": 37
}
```

- [ ] **Step 2: Write failing seconds compiler test**

Assert post-edit style0 has exactly one Pair seq 14 and one Pair seq 15 in the SECONDS target box, donor semantics are gone from those two records, the Pair binding/layout word upper 24 bits are preserved, and styles1–3 remain byte-identical.

- [ ] **Step 3: Implement seconds compiler using only existing Pair records**

Reuse the existing Pair binding primitive to point both records at a numeric font binding whose point size is independent from the main Sprite digits. Do not add images.

- [ ] **Step 4: GREEN regression**

Run inventory, remap, seconds tests plus `PairBindingOverrideTest`.

- [ ] **Step 5: Mark hardware dependency explicitly**

The CI result proves container semantics only. The build report must state: `PAIR_SECONDS_14_15_REQUIRES_HARDWARE_PROOF=1`.

---

### Task 4: Korean AM/PM locale-table extension

**Files:**
- Create: `fitface-layout-golden/Samsung00049LocaleExtensionTest.kt`
- Extend: `fitface-layout-golden/apply_golden_format_patch.py`

**Interfaces:**
- Consumes: donor Pair seq 48, stock `font_ko.bin`, expendable `WF_BMP` font binding.
- Produces:

```kotlin
FaceEditor.extendKoreanAmPmLocale(source: Fit3Container): ContainerEdit
```

and a remapped style0 Pair with sequence 5.

- [ ] **Step 1: Write locale RED tests**

Tests must parse every locale-table descriptor before and after the edit and assert:

- existing weekday/date/degree/percent groups remain byte-for-byte represented;
- `오전` and `오후` are added as complete UTF-8 glyph strings;
- every group offset/length stays in bounds;
- table count and entry size are internally consistent;
- round-trip parse and CRC validation pass;
- a second application fails rather than duplicating groups.

- [ ] **Step 2: Implement a dedicated locale-table rebuilder**

Do not patch offsets ad hoc. Parse descriptors, build the new string payload, recompute descriptor offsets, replace the entry atomically, and let the container serializer update directory offsets/CRCs.

- [ ] **Step 3: Remap donor Pair to source 5**

Use the style-scoped Pair remapper, repurpose the `WF_BMP` binding to an AM/PM role and position it in design-1 `AM_PM = (48,120,25,16)`.

- [ ] **Step 4: GREEN tests**

Run locale + Pair remap + container round-trip regressions.

- [ ] **Step 5: Build report flag**

Emit `AM_PM_SEQ5_REQUIRES_HARDWARE_PROOF=1`.

---

### Task 5: Independent live date parts with stock Composite fallback

**Files:**
- Create: `fitface-layout-golden/Samsung00049DateCompilerTest.kt`
- Extend: `fitface-layout-golden/apply_golden_format_patch.py`

**Interfaces:**
- Consumes: remaining donor Pair records and native 00049 month/day Composite.
- Produces a `DateCompiler` with two explicit modes:

```kotlin
enum class GoldenDateMode { INDEPENDENT_PARTS, STOCK_COMPOSITE_FALLBACK }
```

- [ ] **Step 1: Write RED tests for independent sources**

For `INDEPENDENT_PARTS`, require three live numeric records for seq 24/21/18 and style0-only placement inside `DATE = (65,47,126,17)`. Static `년/월/일` stay in the background artwork.

- [ ] **Step 2: Implement the independent mapping with strict donor accounting**

The compiler must consume only known donor records. If three compatible numeric records are not available after seconds + AM/PM allocation, fail closed and select `STOCK_COMPOSITE_FALLBACK` rather than creating a new record blindly.

- [ ] **Step 3: Implement fallback contract**

Fallback keeps the native 00049 date Composite live, repositions it into the DATE box and emits `DATE_MODE=STOCK_COMPOSITE_FALLBACK` in the build report.

- [ ] **Step 4: Run GREEN**

Both modes must validate; CI selects independent mode only when the structural preconditions hold.

- [ ] **Step 5: Hardware proof flag**

If independent mode is selected, emit `PAIR_DATE_24_21_18_REQUIRES_HARDWARE_PROOF=1`.

---

### Task 6: Weather frame mapping and image-count-neutral Korean state composition

**Files:**
- Create: `fitface-layout-golden/extract_00049_weather_frames.py`
- Create: `fitface-layout-golden/weather_frame_labels_ko.json`
- Create: `fitface-layout-golden/Samsung00049WeatherRewriteTest.kt`
- Extend: `fitface-layout-golden/apply_golden_format_patch.py`

**Interfaces:**
- Consumes: stock style0 Sprite seq 69 and its 24 frame pointers.
- Produces: exactly 24 rewritten frames preserving frame index and image-record count.

- [ ] **Step 1: Extract and fingerprint all 24 stock frames**

The extractor writes a deterministic report containing frame index, referenced relative image offset, dimensions, format and SHA-256. It must detect reused rasters rather than assuming all 24 pointers are unique.

- [ ] **Step 2: Lock `weather_frame_labels_ko.json`**

Every frame index 0..23 must have an explicit Korean label; no default/fallback string is allowed. Mapping must be reviewed against the extracted stock icons before production rewrite.

- [ ] **Step 3: Write structural rewrite tests**

Assert the weather Sprite still has 24 frame pointers, total image-record count is unchanged, pointer reuse relationships remain valid where intended, and every rewritten image validates in its original RGB565/RGB565+A schema.

- [ ] **Step 4: Compose icon + Korean state wording without generative editing**

Use deterministic raster operations only. Preserve the stock weather symbol content and add the mapped Korean label into the allotted weather region; resize/reframe to design-1 WEATHER target without appending images.

- [ ] **Step 5: Run GREEN and produce a contact-sheet artifact**

The contact sheet is a diagnostic artifact only; it does not change production bytes.

---

### Task 7: Golden style0 layout solver and clean-plate assembly

**Files:**
- Create: `fitface-layout-golden/Samsung00049GoldenLayoutTest.kt`
- Create: `fitface-layout-golden/build_clean_plate.py`
- Create: `fitface-layout-golden/apply_golden_layout.py`
- Consume at build time: `fitface-layout/layout_recipes_v1.json`
- Consume local/source asset: design 1 full artwork, 978×1536

**Interfaces:**
- Consumes: Golden recipe + semantic compilers from Tasks 3–6.
- Produces: one edited `style0.bin` with design-1 geometry and a 256×402 clean-plate background.

- [ ] **Step 1: Build clean plate deterministically**

Downscale the full 978×1536 design to 256×402 using a fixed high-quality resampler. Remove only the sample dynamic-value pixels inside the measured live-value boxes using deterministic local background reconstruction/masking; keep bezel, frame, separators, labels and static punctuation.

- [ ] **Step 2: Write failing group-layout tests**

Require style0 semantic groups to land in these design-1 boxes:

```text
DATE            65,47 126x17
WEEKDAY         107,80 42x14
AM_PM           48,120 25x16
TIME            77,139 127x73
SECONDS         48,257 47x30
WEATHER_ICON    98,253 59x46
WEATHER_TEXT    112,301 37x16
TEMP            171,260 42x25
BATTERY_ICON    47,337 27x20
BATTERY_PERCENT 82,336 35x21
```

- [ ] **Step 3: Implement style0-only placement**

Use the native Sprite digit pool for seq 2/3/10/11, resize that pool once, then derive the four digit origins from the TIME group. Keep the colon static in the clean plate. Move weekday, temperature, weather, battery and remapped Pair fields independently.

- [ ] **Step 4: Prove style isolation**

Hash raw `style1.bin`, `style2.bin`, `style3.bin` before and after Golden compilation and require exact equality.

- [ ] **Step 5: Validate size and container integrity**

Require reparse success, CRC success, stable image-count policy and final face container below 4 MiB.

---

### Task 8: Reapply approved LCD colour lock and build Golden APK

**Files:**
- Create/Finalize: `.github/workflows/build-fitface-four-style-golden.yml`
- Extend: `fitface-layout-golden/Samsung00049GoldenLayoutTest.kt`

**Interfaces:**
- Consumes: pinned upstream, existing Foundation/v11 patch pipeline, Golden layout helper tree.
- Produces: coexistable Android debug APK and a Golden watch-face diagnostic package/artifacts.

- [ ] **Step 1: Clone pinned upstream and apply the existing Foundation/v11 stack unchanged**

Use `fitface-build/run_manifest.py` and the existing manifest rather than duplicating patch order in the new workflow.

- [ ] **Step 2: Apply Golden semantic/layout patches before the final optical colour lock**

The workflow must make the order explicit in logs and assert the approved values after all layout edits:

```text
logical #B8B8AD
optical #B5B6BD
RGB565 0xB5B7
```

- [ ] **Step 3: Use a coexistable app ID**

Use `dev.fitface.studio.layoutgolden` for this hardware proof APK so it can coexist with the approved v11/v12 builds.

- [ ] **Step 4: Run focused and broad regressions**

Run:

```bash
./gradlew --no-daemon :core:format:testDebugUnitTest
./gradlew --no-daemon :feature:editor:testDebugUnitTest
./gradlew --no-daemon :app:assembleDebug
```

The Golden-specific tests must run in the same completed workflow.

- [ ] **Step 5: Upload artifacts**

Upload:

```text
FitFace-Studio-Fit3-FourStyle-Golden-D1.apk
Golden-style0-container.bin
Golden-build-report.txt
Golden-weather-contact-sheet.png
```

Record APK/container SHA-256 and workflow run/head SHA.

---

### Task 9: Hardware validation checkpoint

**Files:**
- No production change until hardware result is known.

**Interfaces:**
- Consumes: Golden APK from Task 8 and a real Samsung Galaxy Fit3.
- Produces: pass/fail evidence for the semantic combinations that CI cannot prove.

- [ ] **Step 1: Install the coexistable Golden APK and select design-1 style0**

- [ ] **Step 2: Verify live behavior on the watch**

Check:

```text
seconds: 00..59 rollover
AM/PM: 오전/오후 and noon/midnight transition
weekday: current Korean weekday
full date: current year/month/day and date rollover
battery: percentage changes with watch battery
weather: icon + Korean state wording switch together
temperature: live value
style switching: styles 1–3 remain selectable/unbroken
colour: naked-eye appearance remains the approved v11 tone
```

- [ ] **Step 3: Stop on any semantic failure**

Do not compensate a failed semantic source with fake static content. Report exactly which source/schema failed and use the already-defined fallback path for that subsystem.

- [ ] **Step 4: On full hardware pass, promote compiler to styles1–3**

That promotion is a separate implementation stage using the same semantic code with only recipe/background differences.
