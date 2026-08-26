# FitFace v12 Release Implementation Plan

## Scope
Implement only Stage 2: a reproducible, explicitly signed Release pipeline on top of the verified v12 Foundation. Do not start Stage 3 feature work.

## Locked inputs
- Foundation branch: `work/fitface-v12-foundation`
- Foundation verification HEAD: `7e7f525200fa15e178adaad95b13c8e8417e9bc3`
- Upstream: `satvikgosai/fitface-studio@45a9788d3877627fd5301e9ebba36ef6192d7962`
- Application ID remains `dev.fitface.studio.lcdcomposite.v11`
- Logical UI color remains `#B8B8AD`
- Optical RGB888 remains `#B5B6BD`
- Optical RGB565 remains `0xB5B7`
- Release versionCode: `120000`
- Release versionName: `12.0.0`

## Release signing contract
Formal release publishing requires all four inputs and must never fall back to the Android debug key or a generated throwaway key:
- `FITFACE_RELEASE_KEYSTORE_BASE64`
- `FITFACE_RELEASE_STORE_PASSWORD`
- `FITFACE_RELEASE_KEY_ALIAS`
- `FITFACE_RELEASE_KEY_PASSWORD`

The repository never stores release key material.

## Implementation
1. Add tests first for the Release config patcher and formal workflow contract.
2. Observe RED because the patcher and formal Release workflow do not yet exist.
3. Add `fitface-release/apply_release_config.py` to patch only `app/build.gradle.kts` after the Foundation manifest has run.
4. Add a branch verification workflow that:
   - applies the unchanged Foundation manifest;
   - applies the Release config;
   - proves only `app/build.gradle.kts` differs between Foundation and Release source trees before build;
   - runs Foundation focused regressions and editor regression tests;
   - creates an explicit temporary verification keystore (never presented as the formal release key);
   - builds `assembleRelease` with the explicit verification key;
   - verifies app ID, versionCode, versionName and APK signature;
   - emits a clearly named verification-only artifact and SHA-256.
5. Add a formal tag/manual Release workflow that:
   - refuses to continue if any of the four Release secrets is missing;
   - restores and validates the configured release keystore;
   - applies Foundation + Release patches;
   - reruns regressions;
   - builds and signs `assembleRelease`;
   - verifies certificate/app metadata and hashes;
   - uploads the APK artifact;
   - publishes a GitHub Release only for a v12 release tag.
6. Compare the Release branch against Foundation and verify that all Stage 2 changes are isolated to Release tooling/docs/workflows.

## Completion gate
Stage 2 is complete only when:
- RED was observed for the missing production Release implementation;
- all Release contract tests pass;
- Foundation focused tests pass;
- editor tests pass;
- `assembleRelease` succeeds with an explicit verification key;
- `apksigner verify` succeeds;
- application ID is still `dev.fitface.studio.lcdcomposite.v11`;
- versionCode is `120000` and versionName is `12.0.0`;
- Release artifact SHA-256 is recorded;
- no Stage 3 code is created or modified.
