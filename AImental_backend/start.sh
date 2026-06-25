#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

if grep -qi microsoft /proc/version 2>/dev/null; then
  if powershell.exe -NoProfile -Command "exit 0" >/dev/null 2>&1; then
    backend_dir_windows="$(wslpath -w "$PWD")"
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
      Set-Location -LiteralPath '$backend_dir_windows';
      \$env:PYTHONUTF8 = '1';
      \$env:PYTHONIOENCODING = 'utf-8';
      & '.\.venv\Scripts\python.exe' -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    "
  fi

  echo "This Windows project is configured to run with Git Bash and .venv."
  echo "Your current 'bash' is WSL and Windows interop is disabled."
  echo "Run it from Git Bash, or use:"
  echo '  "C:\Program Files\Git\bin\bash.exe" start.sh'
  exit 1
fi

if [ -f ".venv/Scripts/activate" ]; then
  source ".venv/Scripts/activate"
elif [ -f ".venv/bin/activate" ]; then
  source ".venv/bin/activate"
else
  echo "Missing .venv. Create it first with: uv venv .venv --python 3.11"
  exit 1
fi

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
