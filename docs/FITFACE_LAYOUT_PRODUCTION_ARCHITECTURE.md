# FitFace custom-layout production architecture

## 1. Fixed design coordinate contract

The supplied artwork is 978 x 1536 and the **entire image**, including the metal bezel and outer frame, maps to the full SM-R390 panel at 256 x 402. There is no crop in the baseline transform.

```text
x_fit3 = round(x_source * 256 / 978)
y_fit3 = round(y_source * 402 / 1536)
w_fit3 = round(w_source * 256 / 978)
h_fit3 = round(h_source * 402 / 1536)
```

The first four measured recipes are stored in `fitface-layout/layout_recipes_v1.json`.

## 2. Required live semantics

The production face must keep these values live on the watch rather than baking sample values into the background:

- date: compact `8/27` and/or full Korean layout `2026년 8월 27일`;
- weekday;
- AM/PM as `오전` / `오후`;
- hour and minute;
- seconds;
- battery percentage, with a battery graphic position in the recipe;
- weather-state icon;
- temperature;
- weather-state wording such as `맑음`, `흐림`, `비`, `소나기` when produced from the same live weather state.

Static punctuation and decoration (`:`, `/`, `년`, `월`, `일`, battery outline, frames, bezel, WATER RESIST text) belong in the background clean plate whenever that avoids inventing another live widget.

## 3. What the real Samsung 00003 inspection proved

A fresh Samsung-store package for face `00003` (`Basic dashboard`, store version 4.0.1) was downloaded and its real `style3.bin` was parsed.

The style contains 18 widget records. The relevant live records are:

| Semantic | Real record |
| --- | --- |
| battery value | Pair, global 1, sequence 37, x=-174 y=68 |
| compact month/day date | Composite, global 2, x=134 y=68; inner date sources include 21 and 18 |
| hour tens | Sprite global 3, sequence 2 |
| hour ones | Sprite global 4, sequence 3 |
| minute tens | Sprite global 6, sequence 10 |
| minute ones | Sprite global 7, sequence 11 |
| second tens | Sprite global 9, sequence 14 |
| second ones | Sprite global 10, sequence 15 |
| steps | Pair global 11, sequence 29 |
| temperature | Composite global 12; inner source 62 |

The six clock digit Sprites use the same 38 x 68 RGB565+A digit pool. The Korean glyph table in this face contains only `배터리`, `날짜`, `걸음 수`, `날씨`, `%`, `/`, digits, `°`, and a date-order group. `00003/style3` therefore does **not** contain weekday, AM/PM, a weather-state icon, or all resources needed for the requested layout.

## 4. Full-stock-face scan result

All 100 currently returned Fit3 catalogue products were scanned at the container/sequence level.

Important result:

- `00003 Basic dashboard` is the only scanned digital face exposing the seconds digit sources 14/15 as the stock six-digit clock.
- AM/PM source 5 appears in a separate set of faces (`00106`, `00033`, `00069`, `00100`, `00124`).
- No scanned stock face contains the complete requested set as one ready-made layout.

Therefore this project cannot be implemented as only "move existing widgets in one stock face". A bounded production remap layer is required. It must still preserve the existing fail-closed parser, CRC rebuild, round-trip validation, image-record-count discipline and 4 MiB watch limit.

## 5. Recommended production base: Samsung 00049

`00049 Detailed dashboard` is the best base for this design family because it already contains the expensive live resources that would be hardest to synthesize safely:

- live hour/minute Sprite digit pool;
- live weekday;
- live month/day date data;
- live weather-state Sprite with 24 frames;
- live temperature;
- live battery gauge/percentage;
- multiple metric widgets that are not required by the new design and can be repurposed without first adding a large new raster subsystem.

Its Korean glyph groups already contain seven weekdays, degree, decimal digits, percent and date ordering. Its font bindings include `WF_DATE`, `WF_VALUE`, `WF_BATTARY`, `WF_WEEK` and an expendable metric role (`WF_BMP`) that can be repurposed for AM/PM after the old metric widget is removed.

### 5.1 Native `00049/style0` semantic inventory

| Global | Type | Seq | Current role | Production action |
| ---: | ---: | ---: | --- | --- |
| 0 | Static | 0 | full-panel background | replace with design clean plate |
| 1 | Comp | 0 | month/day | replace for custom date flow or keep as fallback |
| 2 | Pair | 17 | weekday | **keep and reposition** |
| 3 | Sprite | 2 | hour tens | **keep / resize / reposition** |
| 4 | Sprite | 3 | hour ones | **keep / resize / reposition** |
| 5 | Sprite | 10 | minute tens | **keep / resize / reposition** |
| 6 | Sprite | 11 | minute ones | **keep / resize / reposition** |
| 7 | Sprite | 69 | weather state icon | **keep, reframe artwork, reposition** |
| 8 | Comp | 0 | temperature, inner source 62 | **keep and reposition** |
| 9 | Pair | 41 | heart rate | repurpose for a required Pair field |
| 10 | Badge | 37 | battery gauge/bar | keep when a dynamic battery gauge is desired; otherwise hide under clean plate |
| 11 | Comp | 0 | battery %, inner source 37 | **keep and reposition** |
| 12 | type 6 | 29 | steps gauge | remove/hide; resource donor candidate |
| 13 | type 6 | 48 | kcal gauge | remove/hide; resource donor candidate |
| 14 | type 6 | 115 | activity gauge | remove/hide; resource donor candidate |
| 15 | Pair | 29 | steps value | repurpose |
| 16 | Pair | 48 | kcal value | repurpose |
| 17 | Pair | 115 | activity value | repurpose |

The remap must match by type + original sequence + original identity/position before changing any semantic ID. It must never blindly target a global index across unrelated stock faces.

## 6. Production semantic compiler

The compiler is not a new end-user UI feature. It is an internal watch-face production layer placed above the existing format engine.

```text
DesignRecipe
    -> SemanticPlan
    -> StockFaceResolver(00049)
    -> CleanPlateBackground
    -> DateCompiler
    -> WeekdayPlacement
    -> AmPmCompiler
    -> MainTimeCompiler
    -> SecondsCompiler
    -> BatteryCompiler
    -> WeatherCompiler
    -> approved LCD-tone pass
    -> reparse + CRC + round-trip + 4 MiB validation
    -> preview
    -> hardware test
```

Every stage operates on a fresh pristine base and the whole recipe is committed atomically. Any failed semantic lookup, out-of-range coordinate, unsupported record schema, validation error or size violation aborts the entire build.

## 7. Layout rules

### 7.1 Main time

The main `HH:MM` area uses native Sprite sources 2, 3, 10 and 11. All four main digits share one glyph pool and therefore share one raster size.

The recipe stores the bounding box for the whole `TIME` group. The compiler derives:

- common digit height from the group height;
- common digit width from the source glyph aspect ratio;
- four digit positions;
- fixed colon position.

The colon is static punctuation in the clean-plate background. This avoids adding another live/static record merely to draw a punctuation mark.

### 7.2 Seconds

Seconds are a separate, smaller layout group in all four supplied designs, so they must **not** share a resized raster pool with the large hour/minute Sprites.

Primary experiment:

- repurpose/duplicate two numeric Pair records;
- set their live data-source IDs to second tens/ones (14/15);
- render them through an independently sized numeric font binding;
- position them in the `SECONDS` box.

This keeps the weather image count intact and allows small seconds independent of the large clock. It is a new semantic combination and therefore requires a real Fit3 hardware proof before it becomes the production path.

Fallback if Pair 14/15 does not render correctly:

- preserve image-record count;
- repurpose image records made unused by removed activity widgets into a private small digit pool;
- duplicate two Sprite records using sequences 14/15 and point them at that repurposed pool.

No plan may append a brand-new private Sprite frame set, because changing the Sprite image-record inventory has already produced firmware-level refusal in previous hardware work.

### 7.3 AM/PM

`00049` does not carry AM/PM, but source 5 and the `오전`/`오후` rendering shape are proven by stock face `00106`.

Production plan:

1. repurpose a no-longer-needed Pair record;
2. remap its source to 5;
3. repurpose the expendable `WF_BMP` font binding as `WF_AM_PM`;
4. extend/rebuild locale glyph tables with `오전` and `오후` while preserving all weekday/date/temperature/battery groups still referenced;
5. place it in the recipe's `AM_PM` box.

The glyph-table entry count/offset rebuild must be separately unit-tested and all locale entries must remain internally consistent.

### 7.4 Date

Two recipe modes are required.

`FULL_KO` (designs 1-3):

```text
YEAR + static "년" + MONTH + static "월" + DAY + static "일"
```

`COMPACT_SLASH` (design 4):

```text
MONTH + static "/" + DAY
```

The numeric fields are live; Korean suffixes and slash are static background decoration. The production experiment will use the stock date component IDs observed in Samsung composites (year candidate 24, month 21, day 18) as Pair values so that each component can be positioned independently. The IDs must be verified on hardware before this becomes the final date implementation. Until that proof, the native `00049` month/day Composite remains the safe fallback.

This avoids rewriting the partially-understood Composite word grammar merely to change punctuation.

### 7.5 Weekday

Use native `00049` Pair source 17 and its existing Korean weekday glyph groups. It is moved directly into the recipe `WEEKDAY` box.

### 7.6 Battery

The value remains live through the native `00049` battery path.

- `BATTERY_PERCENT` receives the live percentage Composite/Value.
- The battery outline can be static artwork in the clean plate.
- When a design needs a genuinely changing fill/bar, move and resize the existing battery Badge/gauge instead of faking the fill in the background.

### 7.7 Weather and temperature

Keep native weather Sprite source 69 and temperature source 62.

The stock weather Sprite has 24 state frames. The requested Korean weather wording is best implemented **without inventing another live data source**:

- retain the same 24 frame indices and the same live source 69;
- rewrite each existing weather frame, image-count-neutral, into the design's icon + Korean state wording composition;
- examples include `맑음`, `흐림`, `비`, `소나기`, etc., mapped to the corresponding original weather frame;
- move the resulting Sprite into the weather group;
- keep temperature as a separate live field in `TEMP`.

This makes the text change from the exact same weather state that selects the icon. It also avoids an unsupported extra weather-text widget.

A frame-index -> Korean label table must be established from the 24 extracted stock icon frames before the first production build.

## 8. Size policy by semantic type

| Semantic | Size mechanism |
| --- | --- |
| main HH/MM | resize the shared Sprite digit pool once, then move four widgets |
| seconds | independent Pair font size; fallback private image-count-neutral digit pool |
| AM/PM | font binding point size + Pair bounds/position |
| full/compact date parts | numeric Pair font size/position; fixed suffixes in background |
| weekday | `WF_WEEK` font size/position |
| battery % | native value font size/position |
| battery gauge | native Badge geometry if used |
| weather icon/text | rewrite/resize the existing 24-frame weather pool, keeping count |
| temperature | native temperature field/font size/position |
| background | exactly 256 x 402 |

Record `width/height` fields are not treated as universal rendered size for raster-backed widgets; actual raster dimensions remain authoritative.

## 9. Four current target recipes

The stored `layout_recipes_v1.json` uses these first-pass Fit3 boxes. They are the automatic layout targets before +/-1 to 2 px hardware optical adjustment.

| Slot | D1 | D2 | D3 | D4 |
| --- | --- | --- | --- | --- |
| DATE | 65,47 126x17 | 68,48 120x14 | 76,63 103x12 | 55,90 27x10 |
| WEEKDAY | 107,80 42x14 | 102,75 48x14 | 105,93 50x13 | 105,76 47x15 |
| AM_PM | 48,120 25x16 | 47,107 25x13 | 62,115 20x12 | 47,127 29x13 |
| TIME | 77,139 127x73 | 64,125 143x72 | 81,130 115x67 | 59,149 107x75 |
| SECONDS | 48,257 47x30 | 107,223 47x39 | 107,223 46x38 | 181,180 25x29 |
| WEATHER_ICON | 98,253 59x46 | 172,283 32x23 | 63,286 29x19 | 59,262 32x47 |
| WEATHER_TEXT | 112,301 37x16 | 170,330 36x15 | 97,292 38x12 | 99,272 36x26 |
| TEMP | 171,260 42x25 | 173,312 35x16 | 170,291 31x13 | 169,272 35x26 |
| BATTERY_ICON | 47,337 27x20 | 58,291 34x20 | 82,325 29x14 | 173,66 25x16 |
| BATTERY_PERCENT | 82,336 35x21 | 60,318 34x16 | 140,325 30x13 | 175,88 27x12 |

The boxes are group targets, not an instruction to blindly write record `w/h`. Child glyph coordinates are derived by the semantic compiler according to widget type.

## 10. Colour lock

Layout production must not reopen colour calibration.

- logical editor target: `#B8B8AD`;
- approved Fit3 optical payload: `#B5B6BD`;
- RGB565: `0xB5B7`.

The layout compiler works in semantic/layout space first. The existing approved foreground/raster colour pipeline is applied at the end and regression-locked.

## 11. Implementation order

1. freeze this architecture and recipe schema;
2. build `Samsung00049SemanticInventoryTest` against a real captured 00049 container fixture;
3. add a narrowly-scoped sequence-remap mutator for existing Pair records;
4. prove Pair-based seconds 14/15 in a test build;
5. prove AM/PM source 5 + locale-table extension;
6. prove independent date part values; fallback to stock Composite if needed;
7. extract/map all 24 weather frames and compile icon+Korean-state frames without changing image count;
8. implement the group-layout solver for the four recipes;
9. apply the approved LCD colour pass;
10. run format/editor regressions and build a single Golden Layout hardware APK;
11. hardware-check live rollover (seconds, AM/PM, date), battery change, weather state and style switching;
12. only after the Golden Layout passes, generate the remaining three designs.

## 12. Packaging decision still required

The four designs can be delivered in either of two ways:

- **one face / four styles**: map D1-D4 to style0-style3 of one `00049`-based container. Best for switching designs directly on the Fit3; layout edits are style-specific and must not be broadcast across styles.
- **four independent faces**: one design per resulting face package. Easier isolation, but requires separate identity/package handling and is less convenient to switch.

The production compiler supports both; implementation should not proceed past the Golden Layout packaging boundary until this choice is fixed.
