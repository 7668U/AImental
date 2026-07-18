#!/usr/bin/env python
"""
Stage mini-program assets before uploading them to COS.

It creates:
  output/cos-assets/<COS_ASSET_PREFIX>/...

from the local mini-program asset folders that are referenced through CDN.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = WORKSPACE_ROOT / "AImental_frontend"
BACKEND_ROOT = WORKSPACE_ROOT / "AImental_backend"
OUTPUT_ROOT = WORKSPACE_ROOT / "output" / "cos-assets"
MANIFEST_PATH = WORKSPACE_ROOT / "output" / "cos-assets.manifest.json"
DEFAULT_ASSET_PREFIX = "miniprogram/assets/releases/20260718-1"

COPY_MAP = (
    (FRONTEND_ROOT / "images", Path("images")),
    (FRONTEND_ROOT / "pkgAssessment" / "images", Path("pkgAssessment/images")),
    (FRONTEND_ROOT / "pkgDailyCheckin" / "images", Path("pkgDailyCheckin/images")),
    (FRONTEND_ROOT / "pkgProfile" / "images", Path("pkgProfile/images")),
    (
        FRONTEND_ROOT / "pages" / "daily-checkin" / "assets",
        Path("pages/daily-checkin/assets"),
    ),
    (
        FRONTEND_ROOT / "pkgDailyCheckin" / "assets",
        Path("pkgDailyCheckin/assets"),
    ),
    (
        BACKEND_ROOT / "static" / "avatars",
        Path("backend/avatars"),
    ),
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def copy_tree(source: Path, target: Path) -> tuple[int, int]:
    if not source.exists():
        print(f"skip missing source: {source}")
        return 0, 0

    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    files = [path for path in target.rglob("*") if path.is_file()]
    total_size = sum(path.stat().st_size for path in files)
    return len(files), total_size


def build_manifest(asset_root: Path, asset_prefix: str) -> None:
    assets = []
    for path in sorted(asset_root.rglob("*")):
        if not path.is_file():
            continue
        key = path.relative_to(OUTPUT_ROOT).as_posix()
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        assets.append(
            {
                "key": key,
                "asset_prefix": asset_prefix,
                "size": path.stat().st_size,
                "sha256": digest.hexdigest(),
                "content_type": mimetypes.guess_type(path.name)[0],
            }
        )

    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "asset_prefix": asset_prefix,
                "count": len(assets),
                "assets": assets,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    load_dotenv(WORKSPACE_ROOT / ".env")
    asset_prefix = os.environ.get("COS_ASSET_PREFIX", DEFAULT_ASSET_PREFIX).strip("/")
    asset_root = OUTPUT_ROOT.joinpath(*asset_prefix.split("/"))

    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    asset_root.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_size = 0
    for source, relative_target in COPY_MAP:
        target = asset_root / relative_target
        count, size = copy_tree(source, target)
        total_files += count
        total_size += size
        print(f"{source.relative_to(WORKSPACE_ROOT)} -> {target.relative_to(WORKSPACE_ROOT)} files={count}")

    build_manifest(asset_root, asset_prefix)
    print(f"staged={OUTPUT_ROOT}")
    print(f"asset_prefix={asset_prefix}")
    print(f"manifest={MANIFEST_PATH}")
    print(f"files={total_files} sizeMB={total_size / 1024 / 1024:.2f}")


if __name__ == "__main__":
    main()
