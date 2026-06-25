# 2026-06-25 - Daily Check-in Multi Photos

## Goal

Respond to frontend handoff `msg-20260625-0004`: daily check-in records need up to 3 persisted photos instead of the legacy single `image_url`.

## Backend Changes

- Added `checkins.image_urls` as a JSON text column, with `image_url` retained as the first-photo compatibility field.
- Added response field `image_urls: string[]` to all check-in responses; old records with only `image_url` are returned as `image_urls: [image_url]`.
- Kept `POST /api/v1/checkin/{checkin_id}/image` as the legacy first-image replacement endpoint.
- Added `POST /api/v1/checkin/{checkin_id}/images` for append uploads.
- Added `PUT /api/v1/checkin/{checkin_id}/images` to set the final image URL list, useful for delete/reorder sync.
- Added `POST` and `PUT /api/v1/checkin/{checkin_id}/images/{image_index}` to replace an existing image or append at the next index.
- Added `DELETE /api/v1/checkin/{checkin_id}/images/{image_index}` to remove one image.
- Enforced a maximum of 3 images per check-in.
- Changed saved check-in image filenames from second-only timestamps to timestamp plus short UUID suffix to avoid same-second collisions.

## Frontend Coordination

- Updated `AImental_frontend/pkgDailyCheckin/record.js` to persist the current three-photo wall.
- Create/update now uploads local photos by final index, then calls `PUT /images` with the final URL list.
- Frontend still parses both `image_urls` and legacy `image_url`.

## Verification

- `AImental_backend/.venv/Scripts/python.exe -m py_compile model/status.py router/status.py`
- `node --check AImental_frontend/pkgDailyCheckin/record.js`
- Imported `router.status` successfully and confirmed new image routes are registered.
- Ran model-level create/set/replace/append-limit/delete/legacy-image compatibility verification against a temporary test check-in and removed the test record afterward.

## Risks / Notes

- Uploaded files are not physically deleted when a photo is removed or replaced; only the check-in URL list is updated. This matches the previous upload behavior and avoids unsafe file deletion during this iteration.
- Frontend currently uses local `http://127.0.0.1:8000` API base in this record page, consistent with its current local development state.
