#!/usr/bin/env python
"""
Upload mini-program image assets to Tencent Cloud COS.

Default source layout:
  output/cos-assets/<COS_ASSET_PREFIX>/...

The COS object key is the path relative to COS_UPLOAD_ROOT, so the example above
uploads to:
  <COS_ASSET_PREFIX>/...
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path


REQUIRED_ENV = ("COS_SECRET_ID", "COS_SECRET_KEY", "COS_REGION", "COS_BUCKET")
CACHE_CONTROL = "public, max-age=31536000, immutable"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env() -> dict[str, str]:
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        raise SystemExit(
            "Missing required env vars: "
            + ", ".join(missing)
            + "\nCopy .env.example to .env and fill the COS settings."
        )
    return {key: os.environ[key] for key in REQUIRED_ENV}


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        raise SystemExit(f"Upload root does not exist: {root}")
    files = [path for path in root.rglob("*") if path.is_file()]
    return sorted(files)


def guess_content_type(path: Path) -> str | None:
    content_type = mimetypes.guess_type(path.name)[0]
    if path.suffix.lower() == ".wxss":
        return "text/css"
    return content_type


def upload_files(files: list[Path], root: Path, env: dict[str, str], dry_run: bool) -> None:
    if dry_run:
        for path in files[:20]:
            print(f"DRY {path.relative_to(root).as_posix()}")
        if len(files) > 20:
            print(f"... {len(files) - 20} more")
        return

    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: cos-python-sdk-v5\n"
            "Install it with: python -m pip install cos-python-sdk-v5"
        ) from exc

    config = CosConfig(
        Region=env["COS_REGION"],
        SecretId=env["COS_SECRET_ID"],
        SecretKey=env["COS_SECRET_KEY"],
        Scheme="https",
    )
    client = CosS3Client(config)

    failed: list[tuple[str, str]] = []
    for index, path in enumerate(files, 1):
        key = path.relative_to(root).as_posix()
        kwargs = {
            "Bucket": env["COS_BUCKET"],
            "LocalFilePath": str(path),
            "Key": key,
            "PartSize": 10,
            "MAXThread": 8,
            "EnableMD5": True,
            "CacheControl": CACHE_CONTROL,
        }

        # The SDK can infer most types; this fallback keeps old SDK versions happy.
        content_type = guess_content_type(path)
        if content_type:
            kwargs["ContentType"] = content_type

        for attempt in range(3):
            try:
                client.upload_file(**kwargs)
                break
            except TypeError:
                kwargs.pop("ContentType", None)
                kwargs.pop("CacheControl", None)
                try:
                    client.upload_file(**kwargs)
                    break
                except Exception as exc:  # noqa: BLE001
                    error = exc
            except Exception as exc:  # noqa: BLE001
                error = exc

            if attempt < 2:
                time.sleep(1 + attempt)
        else:
            failed.append((key, str(error)))

        if index % 25 == 0 or index == len(files):
            print(f"progress {index}/{len(files)}")

    if failed:
        print(f"uploaded={len(files) - len(failed)} failed={len(failed)}")
        for key, error in failed[:20]:
            print(f"FAILED {key}: {error[:300]}")
        raise SystemExit(1)


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_cdn(files: list[Path], root: Path, sample_count: int | None) -> None:
    cdn_base = os.environ.get("COS_CDN_BASE_URL", "").rstrip("/")
    if not cdn_base or sample_count == 0:
        return

    sample = files if sample_count is None else files[:sample_count]
    print(f"verifying {len(sample)} CDN URL(s) with full GET and SHA-256")
    failed: list[tuple[str, str]] = []
    for path in sample:
        key = path.relative_to(root).as_posix()
        url = f"{cdn_base}/{key}"
        expected_size = path.stat().st_size
        expected_hash = calculate_sha256(path)

        for attempt in range(3):
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "Accept-Encoding": "identity",
                        "Cache-Control": "no-cache",
                        "User-Agent": "FeelYourselfAssetVerifier/1.0",
                    },
                )
                digest = hashlib.sha256()
                downloaded_size = 0
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    content_length = response.headers.get("Content-Length")
                    if status >= 400:
                        raise RuntimeError(f"HTTP {status}")
                    if content_length and int(content_length) != expected_size:
                        raise RuntimeError(
                            f"Content-Length {content_length} != local {expected_size}"
                        )
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        downloaded_size += len(chunk)
                        digest.update(chunk)

                if downloaded_size != expected_size:
                    raise RuntimeError(
                        f"downloaded {downloaded_size} bytes != local {expected_size}"
                    )
                if digest.hexdigest() != expected_hash:
                    raise RuntimeError("SHA-256 mismatch")
                print(f"OK {key} bytes={downloaded_size}")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    failed.append((key, str(exc)))
                else:
                    time.sleep(1 + attempt)

    if failed:
        print(f"verified={len(sample) - len(failed)} failed={len(failed)}")
        for key, error in failed[:20]:
            print(f"VERIFY_FAILED {key}: {error}")
        raise SystemExit(1)
    print(f"verified={len(sample)} failed=0")


def parse_verify_count(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    count = int(normalized)
    if count < 0:
        raise argparse.ArgumentTypeError("--verify must be 0, a positive number, or all")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload COS/CDN mini-program assets.")
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to env file. Default: .env",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Upload root. Default: COS_UPLOAD_ROOT from env or output/cos-assets",
    )
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading.")
    parser.add_argument(
        "--match",
        default=None,
        help="Only upload keys matching this glob, relative to the upload root.",
    )
    parser.add_argument(
        "--verify",
        type=parse_verify_count,
        default=None,
        help="Number of CDN files to fully verify, or 'all'. Default: all",
    )
    args = parser.parse_args()

    load_dotenv(Path(args.env))
    env = require_env()

    root = Path(args.source or os.environ.get("COS_UPLOAD_ROOT", "output/cos-assets")).resolve()
    files = iter_files(root)
    if args.match:
        files = [
            path
            for path in files
            if fnmatch.fnmatch(path.relative_to(root).as_posix(), args.match)
        ]
        if not files:
            raise SystemExit(f"No files matched --match {args.match!r}")
    total_size = sum(path.stat().st_size for path in files)
    print(f"source={root}")
    print(f"bucket={env['COS_BUCKET']} region={env['COS_REGION']}")
    print(f"files={len(files)} sizeMB={total_size / 1024 / 1024:.2f}")

    upload_files(files, root, env, args.dry_run)
    if not args.dry_run:
        print(f"uploaded={len(files)} failed=0")
        verify_cdn(files, root, args.verify)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
