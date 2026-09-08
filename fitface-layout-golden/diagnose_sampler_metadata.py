#!/usr/bin/env python3
"""Compare Galaxy Store thumbnail tuple with device-proven sampler bytes."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import xml.etree.ElementTree as ET

import fetch_face00049_fixture as stock

FACES = ("00046", "00049", "00106")


def metadata_for(face: str) -> dict[str, object]:
    app_id = f"com.samsung.fit3watchface.sm_r390_{face.lstrip('0') or '0'}"
    # Samsung's product IDs are zero-padded to four digits for the known Fit3 catalogue.
    app_id = f"com.samsung.fit3watchface.sm_r390_{int(face):04d}"
    digest = hashlib.sha1((app_id + stock.HASH_SUFFIX).encode("latin1")).digest()
    params = {
        "csc": "NONE",
        "sdkVer": "36",
        "callerId": stock.PLUGIN_PACKAGE,
        "versionCode": stock.PLUGIN_VERSION,
        "mcc": "450",
        "mnc": "10",
        "systemId": str(int(time.time() * 1000) - 24 * 60 * 60 * 1000),
        "extuk": "0123456789abcdef",
        "abiType": "64",
        "deviceId": "SM-R390",
        "loginType": "N",
        "oneUiVersion": "0",
        "cc": "KOR",
        "pd": "0",
        "appInfo": app_id,
        "hashValue": base64.b64encode(digest).decode("ascii"),
    }
    url = stock.STORE_BASE + "stub/gearAppDownload.as?" + urllib.parse.urlencode(params)
    xml = stock.request_bytes(url, limit=512 * 1024)
    root = ET.fromstring(xml)
    app = root.find("appInfo")
    if app is None:
        raise SystemExit(f"{face}: no appInfo")
    values = {child.tag: (child.text or "").strip() for child in app}
    return {
        "face": face,
        "app_id": app_id,
        "resultCode": values.get("resultCode"),
        "versionName": values.get("versionName"),
        "downloadURI_present": bool(values.get("downloadURI")),
    }


def main() -> None:
    out = Path("sampler-metadata.json")
    rows = [metadata_for(face) for face in FACES]
    out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(out.read_text())


if __name__ == "__main__":
    main()
