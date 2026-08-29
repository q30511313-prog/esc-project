#!/usr/bin/env python3
"""Wire the final four-style Golden D5 hardware baseline into the dedicated app."""

from pathlib import Path
import subprocess
import sys


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_d5_hardware_test_patch.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    helper = Path(__file__).resolve().parent

    # D5 inherits D4/style2. Generate and verify the approved D4 clean plate before
    # compiling the D5 production stack so the final APK cannot silently fall back
    # to the stock style2 background.
    subprocess.run(
        [sys.executable, str(helper / "apply_golden_d4_layout.py"), str(root)],
        check=True,
    )

    repository = root / (
        "core/data/src/main/kotlin/dev/fitface/studio/core/data/"
        "WatchFaceRepositoryImpl.kt"
    )

    replace_once(
        repository,
        "import dev.fitface.studio.core.format.Fit3Container\n",
        "import dev.fitface.studio.core.format.Fit3Container\n"
        "import dev.fitface.studio.core.format.GoldenD5HardwareBaseline\n",
        "GoldenD5HardwareBaseline import",
    )

    replace_once(
        repository,
        "        val original = Fit3Container.parse(apk.binary)\n"
        "        val current = editedBinPath\n",
        "        val stock = Fit3Container.parse(apk.binary)\n"
        "        val original = GoldenD5HardwareBaseline.resolve(apk.faceId, stock)\n"
        "        val current = editedBinPath\n",
        "loadSession D5 baseline",
    )

    print("Golden D5 four-style hardware session baseline patch applied")


if __name__ == "__main__":
    main()
