#!/usr/bin/env python3
"""Capture Samsung 00049 package metadata and vendor style previews for hardware diagnosis."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import fetch_face00049_fixture as stock


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: diagnose_face00049_stock.py OUTPUT_DIR")

    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)

    download_uri, expected_size, version = stock.download_metadata()
    apk = stock.request_bytes(download_uri, limit=stock.MAX_PACKAGE_BYTES)
    if len(apk) != expected_size:
        raise SystemExit(
            f"package size mismatch: expected={expected_size} actual={len(apk)}"
        )

    package_sha = hashlib.sha256(apk).hexdigest()
    with zipfile.ZipFile(io.BytesIO(apk)) as archive:
        names = archive.namelist()
        containers = [name for name in names if name.endswith("SM-R390_00049_256x402.bin")]
        if len(containers) != 1:
            raise SystemExit(f"expected one 00049 container, found {containers}")
        container = archive.read(containers[0])
        (out / "SM-R390_00049_stock.bin").write_bytes(container)

        info_name = "assets/bandface_info.json"
        info = archive.read(info_name)
        (out / "bandface_info.json").write_bytes(info)

        previews = []
        prefix = "assets/SM-R390_00049_"
        for name in names:
            if not name.startswith(prefix) or not name.endswith(".png"):
                continue
            # Default package previews live directly under assets/, not locale subdirs.
            if name.count("/") != 1:
                continue
            payload = archive.read(name)
            target = out / Path(name).name
            target.write_bytes(payload)
            previews.append({
                "member": name,
                "file": target.name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })

    report = {
        "version": version,
        "package_bytes": len(apk),
        "package_sha256": package_sha,
        "container_bytes": len(container),
        "container_sha256": hashlib.sha256(container).hexdigest(),
        "previews": previews,
    }
    (out / "stock-diagnostic.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
