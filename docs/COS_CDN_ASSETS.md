# COS/CDN Assets

This project serves most mini-program image assets from Tencent Cloud COS through the CDN domain:

```text
https://assets.feelyourself.cn
```

The current asset prefix is:

```text
miniprogram/assets/releases/20260718-1
```

So an asset stored in COS as:

```text
miniprogram/assets/releases/20260718-1/images/share-cover.png
```

is referenced in the mini-program as:

```text
https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/share-cover.png
```

## Why This Exists

WeChat mini-program upload checks are strict about main-package size and local resource size. Large images are kept out of the uploaded package and loaded from CDN instead.

Current package strategy:

- Keep `AImental_frontend/images/tabbar` local for tabBar icons.
- Upload large image assets to COS/CDN.
- Ignore CDN-backed local image folders through `AImental_frontend/project.config.json`.
- Publish each release under a new immutable prefix. Never overwrite an existing
  release prefix after clients may have cached it.

## Local Env

Real COS credentials live in the local root `.env` file, which is ignored by git.

Required variables:

```bash
COS_SECRET_ID=
COS_SECRET_KEY=
COS_REGION=ap-beijing
COS_BUCKET=feelyourself-assets-1369598469
COS_UPLOAD_ROOT=output/cos-assets
COS_CDN_BASE_URL=https://assets.feelyourself.cn
COS_ASSET_PREFIX=miniprogram/assets/releases/20260718-1
```

Do not commit real credentials. `.env.example` contains placeholders for future setup.

## One-Time Dependency

The upload script uses Tencent Cloud's COS Python SDK:

```bash
python -m pip install cos-python-sdk-v5
```

## Update Assets

Use this flow after adding or replacing images.

1. Put the image in the correct local source folder:

```text
AImental_frontend/images/...
AImental_frontend/pkgAssessment/images/...
AImental_frontend/pkgDailyCheckin/images/...
AImental_frontend/pkgProfile/images/...
AImental_frontend/pages/daily-checkin/assets/...
AImental_frontend/pkgDailyCheckin/assets/...
AImental_backend/static/avatars/...
```

2. Reference it through the CDN URL in mini-program code:

```text
https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/...
```

Examples:

```text
AImental_frontend/images/ai-therapist/plant-buddy.png
-> https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/ai-therapist/plant-buddy.png

AImental_frontend/pkgAssessment/images/category/health-hero.png
-> https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/category/health-hero.png

AImental_frontend/pages/daily-checkin/assets/calendar-hero-bg.png
-> https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pages/daily-checkin/assets/calendar-hero-bg.png

AImental_frontend/pkgDailyCheckin/assets/trajectory/calm.jpg
-> https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgDailyCheckin/assets/trajectory/calm.jpg

AImental_backend/static/avatars/default.png
-> https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/backend/avatars/default.png
```

3. Rebuild the upload staging directory:

```bash
python tools/stage_cos_assets.py
```

This creates:

```text
output/cos-assets/miniprogram/assets/releases/20260718-1/...
```

4. Audit every runtime image reference, staged file, manifest hash, and image
   decoder result:

```bash
python tools/audit_frontend_assets.py
```

5. Dry-run the upload:

```bash
python tools/upload_cos_assets.py --dry-run --verify 0
```

6. Upload to COS and fully download every CDN object to compare its length and
   SHA-256 hash:

```bash
python tools/upload_cos_assets.py --verify all
```

The script reads `.env`, uploads everything under `COS_UPLOAD_ROOT`, enables
upload MD5 checking, and writes `Cache-Control: public, max-age=31536000,
immutable`.

For a quick targeted check during development:

```bash
python tools/upload_cos_assets.py --verify 10
```

Before the next asset release, choose a new `COS_ASSET_PREFIX`, update runtime
references to the same prefix, and run the full flow again. Reusing an existing
prefix can leave CDN edge nodes with stale bodies or byte ranges and may cause
`ERR_CONTENT_LENGTH_MISMATCH`.

## Current WeChat Domain Setup

Mini-program server domain configuration should include:

```text
request合法域名:      https://api.feelyourself.cn
socket合法域名:       wss://api.feelyourself.cn
uploadFile合法域名:   https://api.feelyourself.cn
downloadFile合法域名: https://api.feelyourself.cn
                     https://assets.feelyourself.cn
```

The CDN domain only needs to be in `downloadFile合法域名` for image loading.

## CDN / HTTPS Checks

Useful checks:

```bash
curl -I https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/share-cover.png
curl -I https://feelyourself-assets-1369598469.cos.ap-beijing.myqcloud.com/miniprogram/assets/releases/20260718-1/images/share-cover.png
```

Expected CDN result:

```text
HTTP/1.1 200 OK
```

If COS returns `200 OK` but CDN HTTPS returns `514 Frequency Capped`, check the CDN domain's HTTPS service and certificate binding in Tencent Cloud.

## Package Upload Notes

The upload ignore rules live in:

```text
AImental_frontend/project.config.json
```

Important ignored paths include:

```text
images/ai-therapist
images/assessment
images/daily-checkin
images/icons
images/paper-airplane
images/privacy
images/vip
pkgAssessment/images
pkgDailyCheckin/images
pkgDailyCheckin/assets
pkgProfile/images
pages/daily-checkin/assets
components/components-ecanvas
pkgProfile/history_analysis.*
```

Do not remove these ignore rules unless the corresponding resources are moved back into the mini-program package.

The tabBar icon files remain local because WeChat requires local tabBar paths. This includes
`images/tabbar/*`, `images/community.png`, and `images/community_selected.png`.

## Public Asset Boundary

Only public, application-owned static assets belong in this upload flow. Never stage or upload:

- `.env` or credentials
- databases and backups
- `private_media`
- user-uploaded photos or avatars
- logs and generated user reports

The staging script intentionally copies only the public frontend asset roots listed above.
It also copies the built-in public AI character avatars from `AImental_backend/static/avatars`.

## Security

The current `.env` contains a Tencent Cloud API key with COS upload access. After any one-off upload session, consider disabling or rotating the key in Tencent Cloud CAM if it was shared in chat or copied into another environment.
