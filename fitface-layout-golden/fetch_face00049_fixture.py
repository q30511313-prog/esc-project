#!/usr/bin/env python3
"""Fetch the current Samsung Fit3 00049 container for CI semantic tests.

This helper downloads a public stock watch-face package through the same Galaxy
Store endpoint already used by FitFace. It writes only the SM-R390 256x402
container; no device/user identifier is read. `extuk` is a fixed non-sensitive
Android-ID-shaped test value because the store rejects an empty parameter.
"""

from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

APP_ID = "com.samsung.fit3watchface.sm_r390_0049"
HASH_SUFFIX = "GALAXYAPPSAPI"
STORE_BASE = "https://vas.samsungapps.com/vas/"
PLUGIN_PACKAGE = "com.samsung.wearable.fit3plugin"
PLUGIN_VERSION = "126071051"
MAX_PACKAGE_BYTES = 32 * 1024 * 1024
MAX_CONTAINER_BYTES = 4 * 1024 * 1024
TRUSTED_SUFFIXES = (".samsungapps.com", ".galaxyappstore.com")


def trusted_https(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return host in {"samsungapps.com", "galaxyappstore.com"} or host.endswith(
        TRUSTED_SUFFIXES
    )


def request_bytes(url: str, *, limit: int) -> bytes:
    if not trusted_https(url):
        raise SystemExit(f"untrusted/non-HTTPS Samsung URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        final_url = response.geturl()
        if not trusted_https(final_url):
            raise SystemExit(f"Samsung redirect left trusted hosts: {final_url}")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > limit:
            raise SystemExit(f"response exceeds size limit: {declared} > {limit}")
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise SystemExit(f"response exceeds size limit: > {limit}")
    return payload


def download_metadata() -> tuple[str, int, str]:
    app_info = APP_ID
    digest = hashlib.sha1((app_info + HASH_SUFFIX).encode("latin1")).digest()
    hash_value = base64.b64encode(digest).decode("ascii")
    # The Android implementation sends the wall-clock boot epoch. A deterministic
    # one-day uptime approximation is sufficient for the public stock-face request.
    system_id = str(int(time.time() * 1000) - 24 * 60 * 60 * 1000)
    params = {
        "csc": "NONE",
        "sdkVer": "36",
        "callerId": PLUGIN_PACKAGE,
        "versionCode": PLUGIN_VERSION,
        "mcc": "450",
        "mnc": "10",
        "systemId": system_id,
        "extuk": "0123456789abcdef",
        "abiType": "64",
        "deviceId": "SM-R390",
        "loginType": "N",
        "oneUiVersion": "0",
        "cc": "KOR",
        "pd": "0",
        "appInfo": app_info,
        "hashValue": hash_value,
    }
    url = STORE_BASE + "stub/gearAppDownload.as?" + urllib.parse.urlencode(params)
    xml = request_bytes(url, limit=512 * 1024)
    root = ET.fromstring(xml)
    app = root.find("appInfo")
    if app is None:
        raise SystemExit("Samsung response has no appInfo")

    def text(name: str) -> str:
        node = app.find(name)
        return (node.text or "").strip() if node is not None else ""

    result_code = text("resultCode")
    download_uri = text("downloadURI")
    content_size = int(text("contentSize") or "-1")
    version = text("versionName")
    if result_code != "1" or not download_uri:
        raise SystemExit(
            f"Samsung did not provide 00049: resultCode={result_code!r}"
        )
    if not trusted_https(download_uri):
        raise SystemExit(f"untrusted package URI: {download_uri}")
    if content_size <= 0 or content_size > MAX_PACKAGE_BYTES:
        raise SystemExit(f"invalid package size: {content_size}")
    return download_uri, content_size, version


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fetch_face00049_fixture.py OUTPUT_BIN")
    output = Path(sys.argv[1]).resolve()
    download_uri, expected_size, version = download_metadata()
    apk = request_bytes(download_uri, limit=MAX_PACKAGE_BYTES)
    if len(apk) != expected_size:
        raise SystemExit(
            f"package size mismatch: expected={expected_size} actual={len(apk)}"
        )

    with zipfile.ZipFile(io.BytesIO(apk)) as archive:
        members = [
            name
            for name in archive.namelist()
            if name.endswith("SM-R390_00049_256x402.bin")
        ]
        if len(members) != 1:
            raise SystemExit(f"expected one 00049 container, found {members}")
        container = archive.read(members[0])

    if not container.startswith(b"oppo"):
        raise SystemExit("00049 container has unexpected magic")
    if len(container) <= 32 or len(container) > MAX_CONTAINER_BYTES:
        raise SystemExit(f"00049 container size outside policy: {len(container)}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(container)
    print(f"SAMSUNG_00049_VERSION={version}")
    print(f"SAMSUNG_00049_CONTAINER_BYTES={len(container)}")
    print(f"SAMSUNG_00049_CONTAINER_SHA256={hashlib.sha256(container).hexdigest()}")
    print(f"SAMSUNG_00049_FIXTURE={output}")


if __name__ == "__main__":
    main()
