# FitFace Studio sequence override experiment

Goal: test whether an existing small type-5 VALUE widget on Galaxy Fit3 can be reassigned to a firmware sequence already used by the face (notably the seconds sequences 14/15), without changing widget geometry or adding data sources.

Safety constraints:
- Work only on `tmp-fitface-build`; never merge to `master`.
- Upstream source remains pinned to commit `45a9788d3877627fd5301e9ebba36ef6192d7962`.
- Sequence override is exposed only for type-5 VALUE widgets and only as an explicitly labelled experimental control.
- Default user workflow is selected-style only; the user should keep “Apply widget edits to every style” OFF during hardware tests.
- Same-size binary rewrite only; recalculate entry/container CRCs and validate before installation.

TDD/verification:
1. Add a synthetic format-layer test that expects a VALUE widget sequence rewrite API.
2. Run it before implementation and require failure (RED).
3. Apply the implementation patch.
4. Run the targeted format test plus editor unit tests (GREEN).
5. Build debug APK and verify SHA-256.
6. Hardware behavior remains unproven until the user installs a test face on the SM-R390.