# Private User Media Storage

## Current State

Local development remains on encrypted filesystem storage:

```env
PRIVATE_MEDIA_STORAGE_BACKEND=local
```

The backend is ready for private COS storage, but production must not reuse the
public static-asset bucket or `assets.feelyourself.cn`.

User avatars, check-in photos, and generated emotion color cards use the same
`media:<id>` database reference format. The API returns short-lived signed
URLs, so the mini program does not need to know the storage implementation.

## Tencent Cloud Setup

Create a separate COS bucket for user media:

- same region as the backend where practical
- bucket and object ACL set to private
- anonymous read disabled
- server-side encryption enabled
- backend credential limited to this bucket and the `private-media/v1/*` prefix

If CDN acceleration is needed later, create a separate private-media CDN
domain. Configure private COS origin authentication and CDN URL
authentication. Do not point the public asset domain at private user objects.

## Backend Configuration

Put these values in the backend runtime environment, normally
`AImental_backend/.env` or the deployment secret store:

```env
PRIVATE_MEDIA_STORAGE_BACKEND=cos
PRIVATE_MEDIA_COS_REGION=ap-beijing
PRIVATE_MEDIA_COS_BUCKET=<private-bucket-name>
PRIVATE_MEDIA_COS_SECRET_ID=<private-media-only-secret-id>
PRIVATE_MEDIA_COS_SECRET_KEY=<private-media-only-secret-key>
PRIVATE_MEDIA_COS_SESSION_TOKEN=
PRIVATE_MEDIA_COS_PREFIX=private-media/v1
PRIVATE_MEDIA_URL_TTL_SECONDS=900
PRIVATE_MEDIA_DIRECT_UPLOAD_TTL_SECONDS=300
PRIVATE_MEDIA_CDN_BASE_URL=https://media.feelyourself.cn
PRIVATE_MEDIA_CDN_AUTH_ALGORITHM=sha256
PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM=sign
PRIVATE_MEDIA_CDN_AUTH_UID=0
PRIVATE_MEDIA_CDN_AUTH_PRIMARY_KEY=<cdn-type-a-primary-key>
PRIVATE_MEDIA_CDN_AUTH_BACKUP_KEY=<cdn-type-a-backup-key>
```

Install the pinned SDK from `AImental_backend/requirements.txt`, restart the
backend, then run:

```powershell
cd AImental_backend
python scripts/migrate_private_media_to_cos.py --dry-run
python scripts/migrate_private_media_to_cos.py
```

The migration backs up `user_account.db`, uploads local private media, updates
the storage backend per record, and removes local encrypted copies only after
the corresponding database update succeeds.

When `PRIVATE_MEDIA_CDN_BASE_URL` and an auth key are configured, COS-backed
media responses use Tencent CDN Type A signed URLs. The signature payload is:

```text
sha256(uri-timestamp-rand-uid-key)
```

The query parameter format is:

```text
sign=timestamp-rand-uid-digest
```

Without CDN configuration, the backend falls back to direct private COS
presigned URLs.

## Mini Program Direct Upload

Avatar and check-in image uploads use this flow when
`PRIVATE_MEDIA_STORAGE_BACKEND=cos`:

1. The mini program requests a single-object, short-lived PUT URL from
   `POST /api/v1/private-media/uploads`.
2. The mini program sends the image bytes directly to the private COS bucket
   with `wx.request`.
3. The mini program sends the signed upload token to the avatar or check-in
   confirmation endpoint.
4. The backend verifies token ownership, purpose, expiry, object size, and
   object content type before creating the `media:<id>` record and binding it.

The permanent COS secret is used only by the backend. The upload URL is scoped
to one generated object key and expires after
`PRIVATE_MEDIA_DIRECT_UPLOAD_TTL_SECONDS`.

In the WeChat Mini Program admin console, add the private COS origin domain to
the **request legal domains** list:

```text
https://<private-bucket>.cos.<region>.myqcloud.com
```

The API domain remains required as a request and uploadFile legal domain
because local development and older backends use the legacy upload fallback.

Configure COS CORS for the private bucket so the mini program can send:

```text
Method: PUT
Allowed headers: Content-Type, x-cos-server-side-encryption
```

Do not add the private bucket to the public static-asset staging or CDN upload
scripts.

## Lifecycle Rules

- Replacing an avatar deletes the previous private media object.
- Removing, replacing, or deleting check-in images deletes unreferenced media.
- Failed uploads are cleaned up when possible.
- Local development keeps the encrypted fallback for offline work.
- Existing public emotion color cards were moved into private media storage.
