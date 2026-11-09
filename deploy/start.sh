#!/bin/sh
set -eu

: "${SECRET_KEY:?Set SECRET_KEY in Render environment variables}"
: "${ADMIN_EMAIL:?Set ADMIN_EMAIL in Render environment variables}"
: "${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in Render environment variables}"
: "${DATABASE_URL:?Set DATABASE_URL to your PostgreSQL connection string}"

uvicorn app.main:app --app-dir /app/backend --host 127.0.0.1 --port 8000 &
API_PID=$!
cleanup() { kill "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

/opt/venv/bin/python - <<'PYCODE'
import time
import urllib.error
import urllib.request
url = "http://127.0.0.1:8000/api/health"
for attempt in range(30):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                print("Backend and database health check passed.", flush=True)
                break
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        pass
    time.sleep(1)
else:
    raise SystemExit("Backend did not become healthy. Check SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, and DATABASE_URL.")
PYCODE

cd /app/frontend
exec npm run start -- --hostname 0.0.0.0 --port "${PORT:-10000}"
