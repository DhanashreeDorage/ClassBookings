#!/bin/sh
set -eu
uvicorn app.main:app --app-dir /app/backend --host 127.0.0.1 --port 8000 &
cd /app/frontend
exec npm run start -- --hostname 0.0.0.0 --port "${PORT:-10000}"
