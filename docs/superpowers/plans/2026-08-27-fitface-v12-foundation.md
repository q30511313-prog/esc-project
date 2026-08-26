# FitFace v12 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v11 Stable workflow's scattered patch-order knowledge with one validated JSON manifest and Python runner, while proving that the resulting APK contents are byte-for-byte equivalent entry-by-entry to the approved v11 legacy pipeline.

**Architecture:** `fitface-build/v12-foundation-manifest.json` is the single source of truth for upstream pin, immutable color/application locks, exact 16-step patch sequence, commands, and focused test classes. `fitface-build/run_manifest.py` validates and executes that manifest. CI builds the same pinned upstream twice—once through the unchanged v11 legacy command sequence and once through the manifest runner—and accepts Foundation only when every unzipped APK entry has the same SHA-256.

**Tech Stack:** JSON, Python 3 standard library, unittest, Bash, GitHub Actions, Gradle/JDK 17, Android debug APK.

**Spec:** `docs/superpowers/specs/2026-08-27-fitface-v12-foundation-design.md`

## Global Constraints

- Do not modify `fitface-v11-stable`.
- Upstream repository remains `satvikgosai/fitface-studio` at commit `45a9788d3877627fd5301e9ebba36ef6192d7962`.
- Application ID remains `dev.fitface.studio.lcdcomposite.v11`.
- Logical/UI color remains `#B8B8AD`.
- Samsung 00003/style3 hardware payload remains `#B5B6BD`, RGB565 `0xB5B7`.
- Do not alter the existing alpha-mask, Sequence, Pair Binding, Sprite, Composite, Static, optical-compensation, normalization, or non-sprite patch implementations.
- Do not merge the 16-patch calibration experiment.
- Foundation may add only `fitface-build/**`, `.github/workflows/build-fitface-v12-foundation.yml`, and Foundation spec/plan documentation.

---

### Task 1: RED manifest contract

**Files:**
- Create: `fitface-build/test_manifest.py`
- Create: `.github/workflows/build-fitface-v12-foundation.yml` (RED contract-only version)

**Interfaces:**
- Consumes: repository helper/test files already present on `work/fitface-v12-foundation`.
- Produces: executable unittest contract that requires `v12-foundation-manifest.json` and `run_manifest.py` with the approved locks/order.

- [ ] **Step 1: Add the contract test before production files exist**

The test defines the exact 16 step IDs, exact 13 focused test classes, approved upstream/app/color locks, and asserts the manifest and runner exist. Validation behavior tests cover bad schema, changed locks, duplicate/wrong order, unsupported placeholders, and allowed `{helper}`/`{target}` rendering once the runner exists.

- [ ] **Step 2: Add a minimal RED GitHub Actions workflow**

Run:
```bash
python3 -m unittest discover -s fitface-build -p 'test_*.py' -v
```

Expected result before production files are added: workflow fails with an assertion identifying the missing Foundation manifest/runner, not an unrelated infrastructure failure.

- [ ] **Step 3: Record RED evidence**

Capture workflow run ID, head SHA, failed job/step, and the expected assertion message.

---

### Task 2: GREEN manifest and runner

**Files:**
- Create: `fitface-build/v12-foundation-manifest.json`
- Create: `fitface-build/run_manifest.py`
- Modify: `.github/workflows/build-fitface-v12-foundation.yml`
- Test: `fitface-build/test_manifest.py`

**Interfaces:**
- Consumes: `v12-foundation-manifest.json`, repository helper root, FitFace target root.
- Produces: `load_manifest(path)`, `validate_manifest(manifest)`, `render_command(command, helper_root, target_root)`, `check_required_helper_paths(manifest, helper_root)`, and sequential manifest execution through the CLI.

- [ ] **Step 1: Add the exact JSON manifest**

The manifest must contain schema version 1, the pinned upstream, all four immutable lock values, the exact ordered 16 steps with the current v11 Stable commands, and the exact 13 focused regression classes.

- [ ] **Step 2: Implement strict validation and rendering**

`validate_manifest()` rejects any change to schema/upstream/locks, duplicate or reordered steps, empty commands, focused-test drift, format conversions/specifiers, or placeholders other than `helper` and `target`.

`render_command()` substitutes only resolved helper/target paths. `check_required_helper_paths()` derives every `{helper}/...` source/script path from commands and requires it to exist.

- [ ] **Step 3: Implement sequential execution**

The CLI accepts the manifest path plus `--helper-root`, optional `--target-root`, and `--check`. `--check` performs validation/path checks without executing patches. Normal mode requires an existing target and runs each command through Bash in manifest order, stopping on the first failure and reporting step ID plus command index.

- [ ] **Step 4: Run GREEN unit/contract checks**

Run:
```bash
python3 -m unittest discover -s fitface-build -p 'test_*.py' -v
python3 fitface-build/run_manifest.py fitface-build/v12-foundation-manifest.json --helper-root . --check
```

Expected: both exit 0.

- [ ] **Step 5: Commit GREEN implementation**

Commit message:
```text
feat: add validated FitFace v12 foundation manifest
```

---

### Task 3: Dual-pipeline APK equivalence CI

**Files:**
- Modify: `.github/workflows/build-fitface-v12-foundation.yml`

**Interfaces:**
- Consumes: stable helper tree, Foundation helper tree/manifest/runner, pinned upstream.
- Produces: verified Foundation APK artifact only after legacy/manifest internal-entry equality.

- [ ] **Step 1: Create independent helper and upstream checkouts**

Use `legacy-helper` from `fitface-v11-stable`, `foundation-helper` from `work/fitface-v12-foundation`, and two clean FitFace upstream checkouts at `45a9788d3877627fd5301e9ebba36ef6192d7962`. This prevents the legacy `sed` mutations from contaminating the Foundation helper tree.

- [ ] **Step 2: Apply the legacy v11 pipeline verbatim**

Use the current stable workflow command sequence against only `legacy-fitface-studio`, including all helper/test copies, patch scripts, normalization, bright label, and app-ID substitution.

- [ ] **Step 3: Apply the Foundation manifest pipeline**

Run:
```bash
python3 foundation-helper/fitface-build/run_manifest.py \
  foundation-helper/fitface-build/v12-foundation-manifest.json \
  --helper-root foundation-helper \
  --target-root foundation-fitface-studio
```

- [ ] **Step 4: Run Foundation regressions**

Construct the Gradle focused-test arguments from the manifest's `focused_tests` array and run `:core:format:testDebugUnitTest`. Then run `:feature:editor:testDebugUnitTest`.

- [ ] **Step 5: Build both APKs**

Run `./gradlew --no-daemon :app:assembleDebug` in both FitFace trees.

- [ ] **Step 6: Compare every APK entry**

Use Python `zipfile` + `hashlib.sha256` to require identical entry-name sets and identical raw bytes for every entry. Print entry count and differing count; acceptance requires `differing entry count: 0`.

- [ ] **Step 7: Upload the Foundation artifact**

Copy the Foundation APK to `FitFace-Studio-GSHOCK-LCD-v12-FOUNDATION.apk`, generate its SHA-256 file, and upload both only after the equivalence step succeeds.

---

### Task 4: Foundation completion verification

**Files:**
- No app-producing helper/patch modifications permitted.

**Interfaces:**
- Consumes: Foundation branch and CI results.
- Produces: evidence that Foundation changes architecture only, not app behavior/content.

- [ ] **Step 1: Confirm full CI success**

Verify manifest unit tests, `--check`, focused regressions, editor regression, both APK builds, equivalence comparison, and artifact upload all report success in the same completed run.

- [ ] **Step 2: Compare branch scope against stable**

Use GitHub compare from `fitface-v11-stable` to `work/fitface-v12-foundation`. Allowed paths are only `fitface-build/**`, `.github/workflows/build-fitface-v12-foundation.yml`, and `docs/superpowers/specs|plans/**`. Any existing helper/patch source change is a failure.

- [ ] **Step 3: Record artifact evidence**

Record run ID/head SHA, artifact ID/name, APK size/SHA-256, entry count, and zero-difference result.

- [ ] **Step 4: Preserve Foundation branch for Stage 2**

Do not modify stable. Stage 2 Release-system design starts from the verified Foundation HEAD on a new branch so the sequential 1 → 2 → 3 authorization can continue without disturbing v11 Stable.
