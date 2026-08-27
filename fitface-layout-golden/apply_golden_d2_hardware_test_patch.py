#!/usr/bin/env python3
"""Wire the approved Golden D2 baseline into the dedicated hardware-test app only."""

from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_d2_hardware_test_patch.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    repository = root / (
        "core/data/src/main/kotlin/dev/fitface/studio/core/data/"
        "WatchFaceRepositoryImpl.kt"
    )

    replace_once(
        repository,
        "import dev.fitface.studio.core.format.Fit3Container\n",
        "import dev.fitface.studio.core.format.Fit3Container\n"
        "import dev.fitface.studio.core.format.GoldenD2HardwareBaseline\n",
        "GoldenD2HardwareBaseline import",
    )

    replace_once(
        repository,
        "        val original = Fit3Container.parse(apk.binary)\n"
        "        val current = editedBinPath\n",
        "        val stock = Fit3Container.parse(apk.binary)\n"
        "        val original = GoldenD2HardwareBaseline.resolve(apk.faceId, stock)\n"
        "        val current = editedBinPath\n",
        "loadSession D2 baseline",
    )

    print("Golden D2 hardware-test session baseline patch applied")


if __name__ == "__main__":
    main()
