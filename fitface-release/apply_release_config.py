#!/usr/bin/env python3
"""Apply the locked FitFace v12 Release metadata and signing configuration."""

from __future__ import annotations

import argparse
from pathlib import Path


APP_ID = "dev.fitface.studio.lcdcomposite.v11"
BASE_VERSION_CODE = "17"
BASE_VERSION_NAME = "0.1.1"
RELEASE_VERSION_CODE = "120000"
RELEASE_VERSION_NAME = "12.0.0"

RELEASE_SIGNING_BLOCK = '''
        create("release") {
            val releaseKeystore =
                signingInput("fitface.releaseKeystore", "FITFACE_RELEASE_KEYSTORE")
                    ?: error("Release signing requires fitface.releaseKeystore / FITFACE_RELEASE_KEYSTORE")
            storeFile = rootProject.file(releaseKeystore)
            storePassword =
                signingInput("fitface.releaseStorePassword", "FITFACE_RELEASE_STORE_PASSWORD")
                    ?: error("Release signing requires fitface.releaseStorePassword / FITFACE_RELEASE_STORE_PASSWORD")
            keyAlias =
                signingInput("fitface.releaseKeyAlias", "FITFACE_RELEASE_KEY_ALIAS")
                    ?: error("Release signing requires fitface.releaseKeyAlias / FITFACE_RELEASE_KEY_ALIAS")
            keyPassword =
                signingInput("fitface.releaseKeyPassword", "FITFACE_RELEASE_KEY_PASSWORD")
                    ?: error("Release signing requires fitface.releaseKeyPassword / FITFACE_RELEASE_KEY_PASSWORD")
        }
'''

RELEASE_SIGNING_LINE = '            signingConfig = signingConfigs.getByName("release")\n'


def _replace_one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def _find_block_end(text: str, marker: str) -> int:
    marker_pos = text.find(marker)
    if marker_pos < 0:
        raise ValueError(f"missing block marker: {marker}")
    open_pos = text.find("{", marker_pos)
    if open_pos < 0:
        raise ValueError(f"missing opening brace after: {marker}")

    depth = 0
    for index in range(open_pos, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"unterminated block: {marker}")


def patch_build_gradle(text: str) -> str:
    app_anchor = f'applicationId = "{APP_ID}"'
    if text.count(app_anchor) != 1:
        raise ValueError(f"expected locked applicationId {APP_ID}")

    is_baseline = (
        text.count(f"versionCode = {BASE_VERSION_CODE}") == 1
        and text.count(f'versionName = "{BASE_VERSION_NAME}"') == 1
    )
    is_release = (
        text.count(f"versionCode = {RELEASE_VERSION_CODE}") == 1
        and text.count(f'versionName = "{RELEASE_VERSION_NAME}"') == 1
    )
    if not (is_baseline or is_release):
        raise ValueError("unexpected version metadata drift before v12 Release patch")

    output = text
    if is_baseline:
        output = _replace_one(
            output,
            f"versionCode = {BASE_VERSION_CODE}",
            f"versionCode = {RELEASE_VERSION_CODE}",
            "versionCode",
        )
        output = _replace_one(
            output,
            f'versionName = "{BASE_VERSION_NAME}"',
            f'versionName = "{RELEASE_VERSION_NAME}"',
            "versionName",
        )

    release_signing_marker = 'create("release")'
    if release_signing_marker not in output:
        signing_end = _find_block_end(output, "signingConfigs")
        output = output[:signing_end] + RELEASE_SIGNING_BLOCK + output[signing_end:]
    elif output.count(release_signing_marker) != 1:
        raise ValueError("duplicate release signing configuration")

    if RELEASE_SIGNING_LINE.strip() not in output:
        release_marker = "release {"
        release_pos = output.find(release_marker)
        if release_pos < 0:
            raise ValueError("missing release buildType")
        brace_pos = output.find("{", release_pos)
        output = output[: brace_pos + 2] + RELEASE_SIGNING_LINE + output[brace_pos + 2 :]
    elif output.count(RELEASE_SIGNING_LINE.strip()) != 1:
        raise ValueError("duplicate release signingConfig assignment")

    return output


def apply_to_tree(root: Path) -> Path:
    gradle = root / "app" / "build.gradle.kts"
    if not gradle.is_file():
        raise FileNotFoundError(f"missing Gradle file: {gradle}")
    original = gradle.read_text()
    patched = patch_build_gradle(original)
    if patched != original:
        gradle.write_text(patched)
    return gradle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target_root", type=Path)
    args = parser.parse_args()
    gradle = apply_to_tree(args.target_root)
    print(
        "FitFace v12 Release config applied: "
        f"appId={APP_ID}, versionCode={RELEASE_VERSION_CODE}, "
        f"versionName={RELEASE_VERSION_NAME}, file={gradle}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
