#!/usr/bin/env python
"""Audit mini-program image references against the staged COS release."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = WORKSPACE_ROOT / "AImental_frontend"
BACKEND_ROOT = WORKSPACE_ROOT / "AImental_backend"
STAGING_ROOT = WORKSPACE_ROOT / "output" / "cos-assets"
MANIFEST_PATH = WORKSPACE_ROOT / "output" / "cos-assets.manifest.json"
CDN_ORIGIN = "https://assets.feelyourself.cn"
DEFAULT_ASSET_PREFIX = "miniprogram/assets/releases/20260718-1"

RUNTIME_EXTENSIONS = {".js", ".json", ".py", ".wxml", ".wxss"}
ASSET_EXTENSIONS = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".ogg",
    ".png",
    ".svg",
    ".webp",
}
IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
CDN_URL_PATTERN = re.compile(
    r"https://assets\.feelyourself\.cn/[A-Za-z0-9_./-]+"
)
IMAGE_SRC_PATTERN = re.compile(
    r"<image\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1",
    re.IGNORECASE | re.DOTALL,
)
ICON_PATH_PATTERN = re.compile(
    r'"(?:selectedIconPath|iconPath)"\s*:\s*"([^"]+)"'
)
SCALE_ICON_OVERRIDES = {
    "SOUL-DRINK": "soul-drink-v2",
}

SOURCE_MAP = (
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
    (BACKEND_ROOT / "static" / "avatars", Path("backend/avatars")),
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_runtime_files() -> list[Path]:
    files = []
    for root in (FRONTEND_ROOT, BACKEND_ROOT):
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in RUNTIME_EXTENSIONS:
                continue
            if "__pycache__" in path.parts or "components-ecanvas" in path.parts:
                continue
            files.append(path)
    return files


def validate_manifest(asset_root: Path, errors: list[str]) -> tuple[int, int]:
    if not MANIFEST_PATH.exists():
        errors.append(f"missing manifest: {MANIFEST_PATH}")
        return 0, 0

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assets = manifest.get("assets", [])
    total_size = 0
    for asset in assets:
        path = STAGING_ROOT / Path(asset["key"])
        if not path.is_file():
            errors.append(f"manifest file missing: {asset['key']}")
            continue
        actual_size = path.stat().st_size
        total_size += actual_size
        if actual_size != asset["size"]:
            errors.append(
                f"manifest size mismatch: {asset['key']} "
                f"{actual_size} != {asset['size']}"
            )
        if sha256(path) != asset["sha256"]:
            errors.append(f"manifest hash mismatch: {asset['key']}")

    staged_files = [path for path in asset_root.rglob("*") if path.is_file()]
    if len(staged_files) != len(assets):
        errors.append(
            f"manifest count mismatch: staged={len(staged_files)} manifest={len(assets)}"
        )
    return len(staged_files), total_size


def validate_source_copy(asset_root: Path, errors: list[str]) -> None:
    for source_root, relative_target in SOURCE_MAP:
        if not source_root.exists():
            continue
        for source in source_root.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(source_root)
            staged = asset_root / relative_target / relative
            if not staged.is_file():
                errors.append(
                    f"source asset not staged: "
                    f"{source.relative_to(WORKSPACE_ROOT).as_posix()}"
                )
                continue
            if source.stat().st_size != staged.stat().st_size:
                errors.append(
                    f"staged size differs from source: "
                    f"{source.relative_to(WORKSPACE_ROOT).as_posix()}"
                )


def validate_cdn_references(
    runtime_files: list[Path],
    asset_prefix: str,
    asset_root: Path,
    errors: list[str],
) -> int:
    expected_url_prefix = f"{CDN_ORIGIN}/{asset_prefix}/"
    references: set[str] = set()
    expected_base_url = f"{CDN_ORIGIN}/{asset_prefix}"

    for path in runtime_files:
        text = path.read_text(encoding="utf-8")
        for match in CDN_URL_PATTERN.finditer(text):
            url = match.group(0)
            references.add(url)
            if url == expected_base_url:
                continue
            if not url.startswith(expected_url_prefix):
                errors.append(
                    f"unexpected CDN release in "
                    f"{path.relative_to(WORKSPACE_ROOT).as_posix()}: {url}"
                )
                continue
            relative_url_path = urlsplit(url).path.removeprefix(
                f"/{asset_prefix}/"
            )
            if Path(relative_url_path).suffix.lower() not in ASSET_EXTENSIONS:
                continue
            staged = asset_root / Path(relative_url_path)
            if not staged.is_file():
                errors.append(
                    f"CDN reference missing from staging: {url} "
                    f"({path.relative_to(WORKSPACE_ROOT).as_posix()})"
                )
    return len(references)


def validate_local_references(
    runtime_files: list[Path],
    errors: list[str],
) -> int:
    checked = 0
    for path in runtime_files:
        if path.suffix.lower() not in {".json", ".wxml"}:
            continue
        text = path.read_text(encoding="utf-8")
        values = []
        if path.suffix.lower() == ".wxml":
            values.extend(match.group(2) for match in IMAGE_SRC_PATTERN.finditer(text))
        else:
            values.extend(match.group(1) for match in ICON_PATH_PATTERN.finditer(text))

        for value in values:
            if (
                not value
                or "{{" in value
                or value.startswith(("http://", "https://", "data:", "cloud://", "wxfile://"))
            ):
                continue
            checked += 1
            if value.startswith("/"):
                target = FRONTEND_ROOT / value.lstrip("/")
            else:
                target = path.parent / value
            if not target.resolve().is_file():
                errors.append(
                    f"local image reference missing: {value} "
                    f"({path.relative_to(WORKSPACE_ROOT).as_posix()})"
                )
    return checked


def validate_dynamic_scale_icons(asset_root: Path, errors: list[str]) -> int:
    database_path = BACKEND_ROOT / "db" / "psychological_assessment.db"
    if not database_path.exists():
        errors.append(f"assessment database missing: {database_path}")
        return 0

    connection = sqlite3.connect(
        f"file:{database_path.as_posix()}?mode=ro",
        uri=True,
    )
    try:
        rows = connection.execute(
            "SELECT short_name FROM scales ORDER BY short_name"
        ).fetchall()
    finally:
        connection.close()

    checked = 0
    for (short_name,) in rows:
        icon_name = SCALE_ICON_OVERRIDES.get(
            short_name,
            str(short_name or "default").lower(),
        )
        icon_path = (
            asset_root
            / "pkgAssessment"
            / "images"
            / "scale-icons"
            / f"{icon_name}.png"
        )
        checked += 1
        if not icon_path.is_file():
            errors.append(
                f"dynamic scale icon missing: {short_name} -> "
                f"{icon_path.relative_to(asset_root).as_posix()}"
            )
    return checked


def validate_images(asset_root: Path, errors: list[str]) -> tuple[int, list[str]]:
    try:
        from PIL import Image
    except ImportError:
        return 0, ["Pillow unavailable; skipped image decode verification"]

    verified = 0
    warnings = []
    for path in asset_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            verified += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"invalid image: {path.relative_to(STAGING_ROOT).as_posix()}: {exc}"
            )
        if path.stat().st_size > 2 * 1024 * 1024:
            warnings.append(
                f"large image >2 MiB: "
                f"{path.relative_to(STAGING_ROOT).as_posix()} "
                f"({path.stat().st_size / 1024 / 1024:.2f} MiB)"
            )
    return verified, warnings


def main() -> None:
    load_dotenv(WORKSPACE_ROOT / ".env")
    asset_prefix = os.environ.get("COS_ASSET_PREFIX", DEFAULT_ASSET_PREFIX).strip("/")
    asset_root = STAGING_ROOT.joinpath(*asset_prefix.split("/"))
    errors: list[str] = []

    if not asset_root.exists():
        raise SystemExit(
            f"staged release missing: {asset_root}\n"
            "Run: python tools/stage_cos_assets.py"
        )

    runtime_files = iter_runtime_files()
    staged_count, staged_size = validate_manifest(asset_root, errors)
    validate_source_copy(asset_root, errors)
    cdn_reference_count = validate_cdn_references(
        runtime_files, asset_prefix, asset_root, errors
    )
    local_reference_count = validate_local_references(runtime_files, errors)
    dynamic_scale_icon_count = validate_dynamic_scale_icons(asset_root, errors)
    decoded_count, warnings = validate_images(asset_root, errors)

    print(f"asset_prefix={asset_prefix}")
    print(f"runtime_files={len(runtime_files)}")
    print(f"cdn_references={cdn_reference_count}")
    print(f"local_references={local_reference_count}")
    print(f"dynamic_scale_icons={dynamic_scale_icon_count}")
    print(f"staged_files={staged_count} sizeMB={staged_size / 1024 / 1024:.2f}")
    print(f"decoded_images={decoded_count}")
    for warning in warnings:
        print(f"WARNING {warning}")

    if errors:
        print(f"errors={len(errors)}")
        for error in errors:
            print(f"ERROR {error}")
        raise SystemExit(1)
    print("errors=0")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
