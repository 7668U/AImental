# User Data Encryption Design

## Scope

The backend protects user account identifiers, profile fields, psychological
assessment answers and results, mood check-ins, locations, notes, feedback,
paper-airplane messages, AI conversations, relationship memory, derived
analysis content, and user-uploaded avatars/check-in images.

Static assessment definitions, AI character definitions, internal UUID foreign
keys, timestamps, feature flags, and operational state remain plaintext because
the application must query or sort them and they do not contain user-authored
content by themselves.

## Cryptography

- Sensitive database values use AES-256-GCM with a fresh 96-bit nonce per write.
- The encrypted value format is `enc:<key-version>:<nonce>:<ciphertext+tag>`.
- Each field has a fixed purpose string as authenticated additional data. A
  ciphertext copied into another protected field therefore fails authentication.
- WeChat `openid` and anonymous H5 tokens use a separate HMAC-SHA-256 blind
  index for equality lookup. The encrypted original value is retained only when
  the service must return or exchange it.
- Uploaded user images are encrypted with AES-256-GCM outside the public static
  directory. The mini program receives a short-lived HMAC-signed read URL.
- JWT signing, data encryption, blind indexing, and media URL signing use
  separate keys.

## Key Management

Production should inject keys through a managed secret service or deployment
secret store. Do not commit them to Git or bake them into an image.

```env
SECRET_KEY=<at-least-32-random-characters>
DATA_ENCRYPTION_KEYS={"v1":"<base64-32-byte-key>"}
ACTIVE_DATA_ENCRYPTION_KEY_VERSION=v1
DATA_BLIND_INDEX_KEY=<base64-32-byte-key>
PRIVATE_MEDIA_URL_SIGNING_KEY=<base64-32-byte-key>
```

To rotate encryption keys, add a new entry to `DATA_ENCRYPTION_KEYS`, change
`ACTIVE_DATA_ENCRYPTION_KEY_VERSION`, deploy with both versions available, and
rewrap existing values before retiring the old key. Keep the blind-index key
stable unless a dedicated blind-index migration is performed.

## Privacy Consent

- Login requests must carry an affirmative consent flag and the exact current
  policy version.
- The backend records the current version, policy SHA-256 digest, timestamp,
  source, and an append-only accept/withdraw audit event.
- Existing tokens are blocked with HTTP 428 when consent is missing, withdrawn,
  or belongs to an older policy version.
- The API never returns the WeChat `openid`.

## Migration

From `AImental_backend`:

```powershell
python scripts/migrate_private_data.py --dry-run
python scripts/migrate_private_data.py
```

The migration creates an encrypted backup, migrates local user images to private
encrypted storage, encrypts database values in place, verifies that no configured
field remains plaintext, and only then removes migrated plaintext media files.
The operation is resumable because already encrypted values are detected.

## Operational Requirements

- Use HTTPS only in production.
- Restrict database, backup, key, and private-media filesystem permissions.
- Do not log request bodies, chat messages, assessment answers, locations,
  `openid`, tokens, or decrypted values.
- Define backup retention and account deletion jobs that also remove private
  media and derived analysis data.
- Review the policy text and set the legal operator name and contact channel
  before release.
