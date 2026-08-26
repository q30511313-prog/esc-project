import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "fitface-build"
MANIFEST_PATH = BUILD_DIR / "v12-foundation-manifest.json"
RUNNER_PATH = BUILD_DIR / "run_manifest.py"

EXPECTED_UPSTREAM = {
    "repository": "satvikgosai/fitface-studio",
    "commit": "45a9788d3877627fd5301e9ebba36ef6192d7962",
}
EXPECTED_LOCKS = {
    "application_id": "dev.fitface.studio.lcdcomposite.v11",
    "logical_color": "#B8B8AD",
    "optical_rgb888": "#B5B6BD",
    "optical_rgb565": "0xB5B7",
}
EXPECTED_STEP_IDS = [
    "install-lcd-helpers-tests",
    "sequence-foundation",
    "pair-binding",
    "sprite-pair-lcd-controls",
    "rgb565-alpha-mask",
    "clock-sprite-group",
    "composite-color",
    "static-raster-color",
    "casio-clock-chrome",
    "samsung00003-foreground",
    "samsung00003-v10-optical-baseline",
    "samsung00003-v11-patch15",
    "pair-normalization",
    "hardware-nonsprite",
    "bright-lcd-label",
    "application-id",
]
EXPECTED_FOCUSED_TESTS = [
    "LcdSpriteTintTest",
    "LcdPaletteTest",
    "CompositeColorOverrideTest",
    "StaticRasterTintTest",
    "StaticAlphaMaskTintTest",
    "AnchoredPairColorTest",
    "DuplicateSequencePairColorTest",
    "ClockSpriteColorGroupTest",
    "CasioClockChromeToneTest",
    "Samsung00003ForegroundToneTest",
    "Samsung00003ClockOpticalV11Test",
    "SequenceOverrideTest",
    "PairBindingOverrideTest",
]


def valid_contract():
    return {
        "schema_version": 1,
        "upstream": copy.deepcopy(EXPECTED_UPSTREAM),
        "locks": copy.deepcopy(EXPECTED_LOCKS),
        "steps": [
            {"id": step_id, "commands": [f"echo {step_id}"]}
            for step_id in EXPECTED_STEP_IDS
        ],
        "focused_tests": list(EXPECTED_FOCUSED_TESTS),
    }


class FoundationManifestContractTest(unittest.TestCase):
    def read_manifest(self):
        self.assertTrue(
            MANIFEST_PATH.is_file(),
            f"missing Foundation manifest: {MANIFEST_PATH}",
        )
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def load_runner(self):
        self.assertTrue(
            RUNNER_PATH.is_file(),
            f"missing Foundation runner: {RUNNER_PATH}",
        )
        spec = importlib.util.spec_from_file_location("fitface_manifest_runner", RUNNER_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_manifest_exists_and_locks_approved_values(self):
        manifest = self.read_manifest()
        self.assertEqual(1, manifest["schema_version"])
        self.assertEqual(EXPECTED_UPSTREAM, manifest["upstream"])
        self.assertEqual(EXPECTED_LOCKS, manifest["locks"])

    def test_manifest_has_exact_patch_step_order(self):
        manifest = self.read_manifest()
        self.assertEqual(EXPECTED_STEP_IDS, [step["id"] for step in manifest["steps"]])
        self.assertEqual(len(EXPECTED_STEP_IDS), len(set(EXPECTED_STEP_IDS)))

    def test_manifest_has_exact_focused_regression_list(self):
        manifest = self.read_manifest()
        self.assertEqual(EXPECTED_FOCUSED_TESTS, manifest["focused_tests"])

    def test_runner_exists_and_accepts_valid_contract(self):
        runner = self.load_runner()
        runner.validate_manifest(valid_contract())

    def test_runner_rejects_schema_drift(self):
        runner = self.load_runner()
        manifest = valid_contract()
        manifest["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "schema_version"):
            runner.validate_manifest(manifest)

    def test_runner_rejects_upstream_or_lock_drift(self):
        runner = self.load_runner()
        manifest = valid_contract()
        manifest["upstream"]["commit"] = "deadbeef"
        with self.assertRaisesRegex(ValueError, "upstream"):
            runner.validate_manifest(manifest)

        manifest = valid_contract()
        manifest["locks"]["optical_rgb565"] = "0x0000"
        with self.assertRaisesRegex(ValueError, "locks"):
            runner.validate_manifest(manifest)

    def test_runner_rejects_duplicate_or_reordered_steps(self):
        runner = self.load_runner()
        manifest = valid_contract()
        manifest["steps"][1]["id"] = manifest["steps"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            runner.validate_manifest(manifest)

        manifest = valid_contract()
        manifest["steps"][0], manifest["steps"][1] = manifest["steps"][1], manifest["steps"][0]
        with self.assertRaisesRegex(ValueError, "order"):
            runner.validate_manifest(manifest)

    def test_runner_rejects_unsupported_placeholder(self):
        runner = self.load_runner()
        manifest = valid_contract()
        manifest["steps"][0]["commands"] = ["echo {home}"]
        with self.assertRaisesRegex(ValueError, "placeholder"):
            runner.validate_manifest(manifest)

    def test_runner_renders_only_helper_and_target_placeholders(self):
        runner = self.load_runner()
        rendered = runner.render_command(
            "python3 {helper}/tool.py {target}",
            Path("/tmp/helper root"),
            Path("/tmp/target root"),
        )
        self.assertIn("/tmp/helper root", rendered)
        self.assertIn("/tmp/target root", rendered)
        self.assertNotIn("{helper}", rendered)
        self.assertNotIn("{target}", rendered)

    def test_manifest_required_helper_paths_exist(self):
        runner = self.load_runner()
        manifest = self.read_manifest()
        runner.validate_manifest(manifest)
        missing = runner.check_required_helper_paths(manifest, ROOT)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
