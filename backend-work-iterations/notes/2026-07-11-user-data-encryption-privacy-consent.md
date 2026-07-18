# 2026-07-11 User Data Encryption And Privacy Consent

## Backend

- Added versioned AES-256-GCM field encryption with per-field authenticated
  purpose strings.
- Added HMAC-SHA-256 blind indexes for WeChat `openid` and anonymous H5 tokens.
- Encrypted account profile data, check-ins, locations, assessments, analysis,
  chats, AI memory, notes, feedback, paper airplanes, and promotion answers.
- Moved user-uploaded avatars and check-in images out of `/static` into encrypted
  private media storage with short-lived signed read URLs.
- Removed `openid` from `/users/me`.
- Replaced the JWT fallback secret with required environment configuration.
- Added versioned privacy policy, immutable consent audit events, withdrawal,
  and HTTP 428 gating for missing, withdrawn, or outdated consent.
- Disabled file logging by default and removed raw model responses from logs.

## Migration

`scripts/migrate_private_data.py` creates authenticated encrypted backups,
migrates media, encrypts configured values, verifies plaintext counts, and
removes orphan plaintext user media.

The local migration completed successfully with zero configured plaintext
values remaining across active and legacy SQLite files.

## Verification

- Encryption randomness, round-trip, and tamper detection.
- Unique `openid` blind indexes for all users.
- Login, withdraw, blocked access, and re-consent API flow.
- Transparent ORM reads across chats, assessments, check-ins, and users.
- Encrypted private media storage and signed URL retrieval.
