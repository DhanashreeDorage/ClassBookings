# Royaltica Publishing — Morning Class Booking (Premium SaaS Upgrade)

This is an upgrade of the existing Royaltica Morning Class Booking starter. It retains the Next.js + FastAPI + PostgreSQL architecture and replaces the basic interface with a premium publishing-academy design. The frontend uses Next.js 15.5.29 and React 19.3.1 to stay on patched, supported releases.

## Included

- Premium public booking portal with responsive monthly calendar.
- Premium admin sign-in and booking-management dashboard.
- Daily 8:00–9:00 AM `America/New_York` class sessions (DST-aware date handling).
- Maximum **25 approved students per class date**.
- Pending requests do not reserve a seat; approvals are checked against capacity on the server.
- A class becomes Full when it has 25 approved bookings; cancellations release a seat.
- Public calendar shows approved/pending counts and availability only, never participant details.
- Participants can check status using their email address and booking reference (ROY-000123 format).
- Admin filters by status, date, name, and email; approve/reject/cancel actions.
- Admin API protected by an expiring bearer token.
- Optional SMTP email hooks. Email delivery is not guaranteed until a provider is configured and tested.
- No Google Calendar integration.
- `/health` endpoint for deployment health checks.

## Project structure

- `frontend/` — Next.js App Router + TypeScript UI
- `backend/` — FastAPI + SQLAlchemy API
- `docker-compose.yml` — local development services
- `.env.example` — environment variable template

## Run locally

1. Install Docker Desktop.
2. Copy `.env.example` to `.env` and set `ADMIN_EMAIL`, a secure `SECRET_KEY`, `ADMIN_PASSWORD`, and a PostgreSQL `DATABASE_URL`.
3. For local Docker Compose, set `DATABASE_URL=postgresql+psycopg://royaltica:change-me@db:5432/royaltica`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `FRONTEND_ORIGIN=http://localhost:3000`.
4. Run `docker compose up --build`.
5. Open `http://localhost:3000`; admin page is `/admin`.

Generate a key on macOS/Linux:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Render deployment

The currently deployed Render service is not changed by editing this local source archive. Apply these files to the GitHub repository connected to Render, then deploy.

Configure the following environment variables in Render (use the PostgreSQL **Internal Database URL** for the backend when available):

- `DATABASE_URL` — Render PostgreSQL connection URL. The backend normalizes `postgres://` and `postgresql://` URLs to the psycopg driver automatically.
- `SECRET_KEY` — a random value of at least 32 characters; do not commit it to GitHub or expose it in frontend variables.
- `ADMIN_EMAIL` — administrator login email (also used as the login username).
- `ADMIN_PASSWORD` — a strong unique password.
- `FRONTEND_ORIGIN` — exact public frontend origin, e.g. `https://classbookings.onrender.com` if frontend and backend share one origin.
- `NEXT_PUBLIC_API_URL` — backend base URL used by the browser. If the frontend and backend are served by the same Render service/reverse proxy, configure the API routing consistently.
- Optional SMTP variables listed in `.env.example`.

Set the Render health check path to `/health` for the combined service. For the current single-service Render setup, use the included root `Dockerfile` and `deploy/start.sh`. Set the Render service to use Docker, with the repository root as the build context. The start script requires `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SECRET_KEY`, and `DATABASE_URL`, then starts FastAPI and Next.js in the same container. It proxies `/api/*` and `/health` to FastAPI on localhost. The `ADMIN_EMAIL` value is also the administrator login email. This archive does not automatically change the connected GitHub repository or Render service settings.

## Important database migration note

The upgrade adds a `class_sessions` table for per-date approval locking. SQLAlchemy `create_all` creates this new table on startup but does not alter existing booking columns. Booking references are derived from the existing booking ID, so the status lookup does not require a booking-table schema change. Existing booking records are preserved. Back up your PostgreSQL database before deploying.

The approval-capacity check uses a per-date row lock on PostgreSQL so simultaneous approval requests for the same date are serialized. Pending bookings do not count toward the limit.

## Existing Render build issue addressed

The prior Render log showed a TypeScript error in the admin page caused by redeclaring a variable named `d`. This admin page uses distinct variable names and typed response handling, avoiding that specific compile failure.

## Email and security notes

- The API logs when SMTP is not configured; it does not claim an email was delivered.
- Use HTTPS, a managed PostgreSQL database, encrypted backups, rate limiting/bot protection, monitoring, and a verified sender domain before public production launch.
- Keep secrets only in Render environment variables or a secret manager. Rotate any key that has been shared outside a trusted channel.
- The included bearer token expires after eight hours. Consider individual administrator accounts and MFA for a larger team.

## API endpoints

- `GET /health`
- `GET /api/public/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /api/bookings/status?email=...&reference=ROY-000123`
- `POST /api/bookings`
- `POST /api/admin/login`
- `GET /api/admin/bookings?status=Pending&class_date=YYYY-MM-DD&q=search` (bearer token)
- `POST /api/admin/bookings/{id}/approve`
- `POST /api/admin/bookings/{id}/reject`
- `POST /api/admin/bookings/{id}/cancel`
