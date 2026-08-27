#!/usr/bin/env python3
"""Wire the Golden D1 baseline into the dedicated hardware-test app only.

This patch is intentionally kept separate from the normal FitFace/v11/v12 build stack.
It fails closed against the pinned upstream source shape and changes only session loading:
Samsung 00049 uses GoldenHardwareBaseline; every other face remains the stock object.
"""

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
        raise SystemExit("usage: apply_golden_hardware_test_patch.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    repository = root / (
        "core/data/src/main/kotlin/dev/fitface/studio/core/data/"
        "WatchFaceRepositoryImpl.kt"
    )

    replace_once(
        repository,
        "import dev.fitface.studio.core.format.Fit3Container\n",
        "import dev.fitface.studio.core.format.Fit3Container\n"
        "import dev.fitface.studio.core.format.GoldenHardwareBaseline\n",
        "GoldenHardwareBaseline import",
    )

    replace_once(
        repository,
        "        val original = Fit3Container.parse(apk.binary)\n"
        "        val current = editedBinPath\n",
        "        val stock = Fit3Container.parse(apk.binary)\n"
        "        val original = GoldenHardwareBaseline.resolve(apk.faceId, stock)\n"
        "        val current = editedBinPath\n",
        "loadSession baseline",
    )

    print("Golden D1 hardware-test session baseline patch applied")


if __name__ == "__main__":
    main()
