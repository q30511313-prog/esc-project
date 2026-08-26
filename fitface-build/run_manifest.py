#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re
import shlex
import string
import subprocess
import sys

APPROVED_UPSTREAM = {
    "repository": "satvikgosai/fitface-studio",
    "commit": "45a9788d3877627fd5301e9ebba36ef6192d7962",
}
APPROVED_LOCKS = {
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
ALLOWED_PLACEHOLDERS = {"helper", "target"}
HELPER_PATH_PATTERN = re.compile(r"\{helper\}/([A-Za-z0-9_.+\-/]+)")
FORMATTER = string.Formatter()


def load_manifest(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"manifest file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    return data


def _validate_command_placeholders(command, step_id, command_index):
    try:
        fields = list(FORMATTER.parse(command))
    except ValueError as exc:
        raise ValueError(
            f"step {step_id} command {command_index}: invalid placeholder syntax: {exc}"
        ) from exc

    for _, field_name, format_spec, conversion in fields:
        if field_name is None:
            continue
        if field_name not in ALLOWED_PLACEHOLDERS:
            raise ValueError(
                f"step {step_id} command {command_index}: unsupported placeholder {{{field_name}}}"
            )
        if format_spec:
            raise ValueError(
                f"step {step_id} command {command_index}: placeholder format specifiers are not supported"
            )
        if conversion:
            raise ValueError(
                f"step {step_id} command {command_index}: placeholder conversions are not supported"
            )


def validate_manifest(manifest):
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be exactly 1")

    if manifest.get("upstream") != APPROVED_UPSTREAM:
        raise ValueError(
            f"upstream must remain locked to {APPROVED_UPSTREAM!r}"
        )

    if manifest.get("locks") != APPROVED_LOCKS:
        raise ValueError(f"locks must remain exactly {APPROVED_LOCKS!r}")

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        raise ValueError("steps must be an array")

    step_ids = []
    for step_index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step {step_index} must be an object")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise ValueError(f"step {step_index} id must be a non-empty string")
        step_ids.append(step_id)

        commands = step.get("commands")
        if not isinstance(commands, list) or not commands:
            raise ValueError(f"step {step_id}: commands must be a non-empty array")
        for command_index, command in enumerate(commands, start=1):
            if not isinstance(command, str) or not command.strip():
                raise ValueError(
                    f"step {step_id} command {command_index}: command must be a non-empty string"
                )
            _validate_command_placeholders(command, step_id, command_index)

    if len(step_ids) != len(set(step_ids)):
        raise ValueError("duplicate step id detected")

    if step_ids != EXPECTED_STEP_IDS:
        raise ValueError(
            "step order must remain exact: " + ", ".join(EXPECTED_STEP_IDS)
        )

    if manifest.get("focused_tests") != EXPECTED_FOCUSED_TESTS:
        raise ValueError(
            "focused_tests must remain the exact approved v11 regression list"
        )


def render_command(command, helper_root, target_root):
    helper = shlex.quote(str(Path(helper_root).resolve()))
    target = shlex.quote(str(Path(target_root).resolve()))
    return command.format(helper=helper, target=target)


def check_required_helper_paths(manifest, helper_root):
    helper_root = Path(helper_root).resolve()
    missing = []
    seen = set()
    for step in manifest["steps"]:
        for command in step["commands"]:
            for relative in HELPER_PATH_PATTERN.findall(command):
                if relative in seen:
                    continue
                seen.add(relative)
                path = helper_root / relative
                if not path.exists():
                    missing.append(str(path))
    return sorted(missing)


def execute_manifest(manifest, helper_root, target_root):
    helper_root = Path(helper_root).resolve()
    target_root = Path(target_root).resolve()
    if not helper_root.is_dir():
        raise ValueError(f"helper root is not a directory: {helper_root}")
    if not target_root.is_dir():
        raise ValueError(f"target root is not a directory: {target_root}")

    missing = check_required_helper_paths(manifest, helper_root)
    if missing:
        raise ValueError("missing required helper paths: " + ", ".join(missing))

    for step in manifest["steps"]:
        step_id = step["id"]
        total = len(step["commands"])
        for command_index, command in enumerate(step["commands"], start=1):
            rendered = render_command(command, helper_root, target_root)
            print(
                f"[{step_id}] command {command_index}/{total}: {rendered}",
                flush=True,
            )
            completed = subprocess.run(
                rendered,
                shell=True,
                executable="/bin/bash",
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"step {step_id} command {command_index} failed with exit code {completed.returncode}"
                )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate and execute the locked FitFace v12 Foundation manifest"
    )
    parser.add_argument("manifest", help="Path to v12-foundation-manifest.json")
    parser.add_argument(
        "--helper-root",
        required=True,
        help="Repository/helper root containing fitface-lcd-color and related helpers",
    )
    parser.add_argument(
        "--target-root",
        help="FitFace Studio source tree to patch; required unless --check is used",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate manifest and required helper paths without executing commands",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        validate_manifest(manifest)

        helper_root = Path(args.helper_root).resolve()
        if not helper_root.is_dir():
            raise ValueError(f"helper root is not a directory: {helper_root}")

        missing = check_required_helper_paths(manifest, helper_root)
        if missing:
            raise ValueError("missing required helper paths: " + ", ".join(missing))

        if args.check:
            print(
                f"Foundation manifest check passed: {len(manifest['steps'])} steps, "
                f"{len(manifest['focused_tests'])} focused tests"
            )
            return 0

        if not args.target_root:
            raise ValueError("--target-root is required unless --check is used")

        execute_manifest(manifest, helper_root, args.target_root)
        print("Foundation manifest execution completed successfully")
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"Foundation manifest error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
