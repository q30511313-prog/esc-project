import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "fitface-release" / "apply_release_config.py"
FORMAL_WORKFLOW = ROOT / ".github" / "workflows" / "release-fitface-v12.yml"

SAMPLE = '''plugins {\n    alias(libs.plugins.android.application)\n}\n\nfun signingInput(property: String, environment: String): String? =\n    (providers.gradleProperty(property).orNull ?: providers.environmentVariable(environment).orNull)\n        ?.takeIf(String::isNotBlank)\n\nandroid {\n    namespace = "dev.fitface.studio"\n    compileSdk = 36\n\n    signingConfigs {\n        getByName("debug") {\n            signingInput("fit3.debugKeystore", "FIT3_DEBUG_KEYSTORE")?.let { keystore ->\n                storeFile = rootProject.file(keystore)\n                storePassword = signingInput("fit3.debugKeystorePassword", "FIT3_DEBUG_KEYSTORE_PASSWORD") ?: "android"\n                keyAlias = signingInput("fit3.debugKeyAlias", "FIT3_DEBUG_KEY_ALIAS") ?: "androiddebugkey"\n                keyPassword = signingInput("fit3.debugKeyPassword", "FIT3_DEBUG_KEY_PASSWORD") ?: "android"\n            }\n        }\n    }\n\n    defaultConfig {\n        applicationId = "dev.fitface.studio.lcdcomposite.v11"\n        minSdk = 28\n        targetSdk = 36\n        versionCode = 17\n        versionName = "0.1.1"\n    }\n\n    buildTypes {\n        release {\n            isMinifyEnabled = true\n            isShrinkResources = true\n            proguardFiles(\n                getDefaultProguardFile("proguard-android-optimize.txt"),\n                "proguard-rules.pro",\n            )\n        }\n    }\n}\n'''


class ReleaseConfigContractTest(unittest.TestCase):
    def load_patcher(self):
        self.assertTrue(PATCHER.is_file(), f"missing Release patcher: {PATCHER}")
        spec = importlib.util.spec_from_file_location("fitface_release_patcher", PATCHER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_patcher_locks_version_and_application_id(self):
        patcher = self.load_patcher()
        output = patcher.patch_build_gradle(SAMPLE)
        self.assertIn('applicationId = "dev.fitface.studio.lcdcomposite.v11"', output)
        self.assertIn('versionCode = 120000', output)
        self.assertIn('versionName = "12.0.0"', output)
        self.assertNotIn('versionCode = 17', output)
        self.assertNotIn('versionName = "0.1.1"', output)

    def test_patcher_adds_explicit_release_signing_without_debug_defaults(self):
        patcher = self.load_patcher()
        output = patcher.patch_build_gradle(SAMPLE)
        for token in (
            'create("release")',
            'fitface.releaseKeystore',
            'FITFACE_RELEASE_KEYSTORE',
            'fitface.releaseStorePassword',
            'FITFACE_RELEASE_STORE_PASSWORD',
            'fitface.releaseKeyAlias',
            'FITFACE_RELEASE_KEY_ALIAS',
            'fitface.releaseKeyPassword',
            'FITFACE_RELEASE_KEY_PASSWORD',
            'signingConfig = signingConfigs.getByName("release")',
        ):
            self.assertIn(token, output)
        release_block = output.split('create("release")', 1)[1].split('defaultConfig', 1)[0]
        self.assertNotIn('?: "android"', release_block)
        self.assertNotIn('androiddebugkey', release_block)

    def test_patcher_is_idempotent(self):
        patcher = self.load_patcher()
        once = patcher.patch_build_gradle(SAMPLE)
        twice = patcher.patch_build_gradle(once)
        self.assertEqual(once, twice)

    def test_patcher_rejects_application_id_or_version_drift(self):
        patcher = self.load_patcher()
        with self.assertRaises(ValueError):
            patcher.patch_build_gradle(SAMPLE.replace('dev.fitface.studio.lcdcomposite.v11', 'dev.fitface.studio.other'))
        with self.assertRaises(ValueError):
            patcher.patch_build_gradle(SAMPLE.replace('versionCode = 17', 'versionCode = 18'))

    def test_cli_patches_only_requested_gradle_file(self):
        patcher = self.load_patcher()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gradle = root / "app" / "build.gradle.kts"
            gradle.parent.mkdir(parents=True)
            gradle.write_text(SAMPLE)
            sentinel = root / "sentinel.txt"
            sentinel.write_text("unchanged")
            patcher.apply_to_tree(root)
            self.assertEqual("unchanged", sentinel.read_text())
            self.assertIn('versionCode = 120000', gradle.read_text())

    def test_formal_release_workflow_requires_all_four_secrets(self):
        self.assertTrue(FORMAL_WORKFLOW.is_file(), f"missing formal Release workflow: {FORMAL_WORKFLOW}")
        text = FORMAL_WORKFLOW.read_text()
        for secret in (
            'FITFACE_RELEASE_KEYSTORE_BASE64',
            'FITFACE_RELEASE_STORE_PASSWORD',
            'FITFACE_RELEASE_KEY_ALIAS',
            'FITFACE_RELEASE_KEY_PASSWORD',
        ):
            self.assertIn(f'secrets.{secret}', text)
            self.assertIn(f'{secret}:', text)
        self.assertIn('Validate required Release secrets', text)
        self.assertNotIn('DEBUG_KEYSTORE_BASE64', text)
        self.assertNotIn('androiddebugkey', text)
        self.assertNotIn('throwaway', text.lower())
        self.assertNotIn('keytool -genkeypair', text)

    def test_formal_release_workflow_builds_and_verifies_release_variant(self):
        self.assertTrue(FORMAL_WORKFLOW.is_file(), f"missing formal Release workflow: {FORMAL_WORKFLOW}")
        text = FORMAL_WORKFLOW.read_text()
        for token in (
            'v12.*',
            ':app:assembleRelease',
            'apksigner verify',
            'version-code',
            'version-name',
            'dev.fitface.studio.lcdcomposite.v11',
            'FitFace-Studio-GSHOCK-LCD-v12.0.0-RELEASE.apk',
            'sha256sum',
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
