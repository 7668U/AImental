# 2026-06-26 WeChat App Config Rewrite

## Goal

Rewrite the WeChat Mini Program AppID and AppSecret into the backend runtime configuration.

## Changes

- Recreated `AImental_backend/.env` with `WECHAT_APP_ID` and `WECHAT_APP_SECRET`.
- Kept credentials in `.env`, which is ignored by git.

## Verification

- Verified from the `AImental_backend` working directory with `.venv/python.exe` that `python-dotenv` reads the updated `WECHAT_APP_ID`.
- Verified the AppSecret is present with length 32; full secret was not printed in command output.
- `python -m py_compile main.py router/user.py` passed.
