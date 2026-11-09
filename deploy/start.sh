#!/bin/sh
set -eu
: "${ADMIN_EMAIL:?Set ADMIN_EMAIL in Render environment variables}"
: "${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in Render environment variables}"
: "${SECRET_KEY:?Set SECRET_KEY in Render environment variables}"
: "${DATABASE_URL:?Set DATABASE_URL to the Render PostgreSQL connection URL}"
if [ "${#SECRET_KEY}" -lt 32 ]; then
  echo "SECRET_KEY must be at least 32 characters" >&2
  exit 1
fi
export ADMIN_USERNAME="${ADMIN_EMAIL}"
export API_PROXY_TARGET="http://127.0.0.1:8000"
python -m uvicorn app.main:app --app-dir /app/backend --host 127.0.0.1 --port 8000 &
API_PID=$!
cleanup() { kill "${WEB_PID:-}" "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
READY=0
for _ in $(seq 1 30); do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "Booking API exited before becoming healthy" >&2
    wait "$API_PID" || true
    exit 1
  fi
  if python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)' >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "Booking API did not become healthy within 30 seconds" >&2
  exit 1
fi
npm --prefix /app/frontend run start -- --port "${PORT:-10000}" &
WEB_PID=$!
wait "$WEB_PID"
