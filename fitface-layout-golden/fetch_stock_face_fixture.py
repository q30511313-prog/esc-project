#!/usr/bin/env python3
"""Fetch one public Samsung Fit3 stock-face container by face id."""

from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

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
    return host in {"samsungapps.com", "galaxyappstore.com"} or host.endswith(TRUSTED_SUFFIXES)


def request_bytes(url: str, *, limit: int) -> bytes:
    if not trusted_https(url):
        raise SystemExit(f"untrusted/non-HTTPS Samsung URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        final_url = response.geturl()
        if not trusted_https(final_url):
            raise SystemExit(f"Samsung redirect left trusted hosts: {final_url}")
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise SystemExit(f"response exceeds size limit: > {limit}")
    return payload


def resolve_app_id(face_id: str) -> str:
    target = str(int(face_id)).zfill(5)
    params = {
        "imgWidth": "216",
        "imgHeight": "432",
        "startNum": "1",
        "endNum": "100",
        "status": "1",
        "cc": "KOR",
        "extraInfo": "screenshot",
        "callerId": PLUGIN_PACKAGE,
        "locale": "en_US",
        "alignOrder": "recent",
        "contentCategoryID": "0000004252",
        "mcc": "450",
        "mnc": "10",
        "csc": "NONE",
        "deviceId": "SM-R390",
        "sdkVer": "36",
        "pd": "0",
    }
    root = ET.fromstring(
        request_bytes(
            STORE_BASE + "product/getContentCategoryProductList.as?" + urllib.parse.urlencode(params),
            limit=1024 * 1024,
        )
    )
    matches = []
    for app in root.findall("appInfo"):
        app_id = (app.findtext("appId") or "").strip()
        match = re.search(r"sm_r390_(\d{4,5})$", app_id, re.I)
        if match and match.group(1).zfill(5) == target:
            matches.append(app_id)
    if len(matches) != 1:
        raise SystemExit(f"expected one catalog app for {target}, found {matches}")
    return matches[0]


def download_metadata(app_id: str) -> tuple[str, int, str]:
    digest = hashlib.sha1((app_id + HASH_SUFFIX).encode("latin1")).digest()
    params = {
        "csc": "NONE",
        "sdkVer": "36",
        "callerId": PLUGIN_PACKAGE,
        "versionCode": PLUGIN_VERSION,
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
    root = ET.fromstring(
        request_bytes(
            STORE_BASE + "stub/gearAppDownload.as?" + urllib.parse.urlencode(params),
            limit=512 * 1024,
        )
    )
    app = root.find("appInfo")
    if app is None:
        raise SystemExit("Samsung response has no appInfo")
    text = lambda name: ((app.findtext(name) or "").strip())
    if text("resultCode") != "1" or not text("downloadURI"):
        raise SystemExit(f"Samsung did not provide {app_id}: result={text('resultCode')!r}")
    size = int(text("contentSize") or "-1")
    if size <= 0 or size > MAX_PACKAGE_BYTES:
        raise SystemExit(f"invalid package size: {size}")
    return text("downloadURI"), size, text("versionName")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: fetch_stock_face_fixture.py FACE_ID OUTPUT_BIN")
    face = str(int(sys.argv[1])).zfill(5)
    output = Path(sys.argv[2]).resolve()
    app_id = resolve_app_id(face)
    uri, expected, version = download_metadata(app_id)
    apk = request_bytes(uri, limit=MAX_PACKAGE_BYTES)
    if len(apk) != expected:
        raise SystemExit(f"package size mismatch: expected={expected} actual={len(apk)}")
    with zipfile.ZipFile(io.BytesIO(apk)) as archive:
        members = [name for name in archive.namelist() if name.endswith(f"SM-R390_{face}_256x402.bin")]
        if len(members) != 1:
            raise SystemExit(f"expected one {face} container, found {members}")
        container = archive.read(members[0])
    if not container.startswith(b"oppo") or not (32 < len(container) <= MAX_CONTAINER_BYTES):
        raise SystemExit(f"{face} container failed magic/size policy")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(container)
    print(f"SAMSUNG_FACE_ID={face}")
    print(f"SAMSUNG_APP_ID={app_id}")
    print(f"SAMSUNG_VERSION={version}")
    print(f"SAMSUNG_CONTAINER_BYTES={len(container)}")
    print(f"SAMSUNG_CONTAINER_SHA256={hashlib.sha256(container).hexdigest()}")


if __name__ == "__main__":
    main()
