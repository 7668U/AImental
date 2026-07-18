#!/usr/bin/env python
"""
Stage mini-program assets before uploading them to COS.

It creates:
  output/cos-assets/miniprogram/assets/v1/...

from the local mini-program asset folders that are referenced through CDN.
"""

from __future__ import annotations

import shutil
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = WORKSPACE_ROOT / "AImental_frontend"
BACKEND_ROOT = WORKSPACE_ROOT / "AImental_backend"
OUTPUT_ROOT = WORKSPACE_ROOT / "output" / "cos-assets"
ASSET_ROOT = OUTPUT_ROOT / "miniprogram" / "assets" / "v1"

COPY_MAP = (
    (FRONTEND_ROOT / "images", ASSET_ROOT / "images"),
    (FRONTEND_ROOT / "pkgAssessment" / "images", ASSET_ROOT / "pkgAssessment" / "images"),
    (FRONTEND_ROOT / "pkgDailyCheckin" / "images", ASSET_ROOT / "pkgDailyCheckin" / "images"),
    (FRONTEND_ROOT / "pkgProfile" / "images", ASSET_ROOT / "pkgProfile" / "images"),
    (
        FRONTEND_ROOT / "pages" / "daily-checkin" / "assets",
        ASSET_ROOT / "pages" / "daily-checkin" / "assets",
    ),
    (
        FRONTEND_ROOT / "pkgDailyCheckin" / "assets",
        ASSET_ROOT / "pkgDailyCheckin" / "assets",
    ),
    (
        BACKEND_ROOT / "static" / "avatars",
        ASSET_ROOT / "backend" / "avatars",
    ),
)


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


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_size = 0
    for source, target in COPY_MAP:
        count, size = copy_tree(source, target)
        total_files += count
        total_size += size
        print(f"{source.relative_to(WORKSPACE_ROOT)} -> {target.relative_to(WORKSPACE_ROOT)} files={count}")

    print(f"staged={OUTPUT_ROOT}")
    print(f"files={total_files} sizeMB={total_size / 1024 / 1024:.2f}")


if __name__ == "__main__":
    main()
