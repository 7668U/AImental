#!/usr/bin/env python
"""
Upload mini-program image assets to Tencent Cloud COS.

Default source layout:
  output/cos-assets/miniprogram/assets/v1/...

The COS object key is the path relative to COS_UPLOAD_ROOT, so the example above
uploads to:
  miniprogram/assets/v1/...
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path


REQUIRED_ENV = ("COS_SECRET_ID", "COS_SECRET_KEY", "COS_REGION", "COS_BUCKET")


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
            "EnableMD5": False,
        }

        # The SDK can infer most types; this fallback keeps old SDK versions happy.
        content_type = guess_content_type(path)
        if content_type:
            kwargs["ContentType"] = content_type

        try:
            client.upload_file(**kwargs)
        except TypeError:
            kwargs.pop("ContentType", None)
            try:
                client.upload_file(**kwargs)
            except Exception as exc:  # noqa: BLE001
                failed.append((key, str(exc)))
        except Exception as exc:  # noqa: BLE001
            failed.append((key, str(exc)))

        if index % 25 == 0 or index == len(files):
            print(f"progress {index}/{len(files)}")

    if failed:
        print(f"uploaded={len(files) - len(failed)} failed={len(failed)}")
        for key, error in failed[:20]:
            print(f"FAILED {key}: {error[:300]}")
        raise SystemExit(1)


def verify_cdn(files: list[Path], root: Path, sample_count: int) -> None:
    cdn_base = os.environ.get("COS_CDN_BASE_URL", "").rstrip("/")
    if not cdn_base or sample_count <= 0:
        return

    sample = files[:sample_count]
    print(f"verifying {len(sample)} CDN URL(s)")
    for path in sample:
        key = path.relative_to(root).as_posix()
        url = f"{cdn_base}/{key}"
        request = urllib.request.Request(url, method="HEAD")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    print(f"{status} {url}")
                    if status < 400:
                        break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"VERIFY_FAILED {url}: {exc}")
                else:
                    time.sleep(1)


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
        "--verify",
        type=int,
        default=3,
        help="Number of uploaded files to verify through CDN. Default: 3",
    )
    args = parser.parse_args()

    load_dotenv(Path(args.env))
    env = require_env()

    root = Path(args.source or os.environ.get("COS_UPLOAD_ROOT", "output/cos-assets")).resolve()
    files = iter_files(root)
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
