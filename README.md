# Royaltica Publishing Morning Class — Render Edition

A single-service Render deployment containing the modern Royaltica public booking experience, private admin dashboard, FastAPI API, and PostgreSQL-backed persistence.

## Included

- Public booking page and monthly calendar
- Daily 8:00–9:00 AM `America/New_York` class (DST-aware)
- Maximum 25 active requests per date; Pending and Approved reserve seats
- Admin approval workflow: Pending, Approved, Rejected, Cancelled
- Private admin dashboard at `/admin`
- Public calendar exposes seat counts only, never participant details
- Duplicate active booking protection for the same email/date
- Optional SMTP email notifications; the app does not claim delivery unless SMTP send succeeds
- No Google Calendar integration
- One Docker web service: Next.js frontend + FastAPI backend
- Render Blueprint provisions a managed PostgreSQL database and wires its private connection into `DATABASE_URL`

## Database included

The `render.yaml` Blueprint defines a Render-managed PostgreSQL database named `royaltica-classbookings-db` and automatically connects it to the web service through the private `DATABASE_URL` connection string. On first startup, SQLAlchemy creates the `bookings` and `booking_audit` tables and the active-booking uniqueness index.

**Important about existing data:** The Blueprint database is a new, empty database. If your current `classbookings` app already has a PostgreSQL database containing bookings, do not switch `DATABASE_URL` to the new database unless you intend to start fresh. Keep your existing database URL instead, or arrange a database backup and migration first. The application code can use an existing compatible PostgreSQL database too.

The Blueprint currently uses Render's Free Postgres plan for a low-cost test deployment. Render Free Postgres is limited to 1 GB and expires 30 days after creation; it has no backups. Upgrade the database to a paid plan before using this for real ongoing bookings. See [Render's Free instance limitations](https://render.com/docs/free).

## Deploy to your existing Render service

This package is configured for the existing Render service named `classbookings` and the public URL can remain `https://classbookings.onrender.com` if you deploy it to that same service.

1. Download and extract this ZIP.
2. Replace the contents of the GitHub repository connected to your existing `classbookings` Render service with the contents of this folder. Keep the project files at the repository root (Dockerfile, render.yaml, backend/, frontend/, deploy/).
3. Commit and push the changes to the branch Render deploys.
4. In Render Dashboard, open `classbookings` → **Settings** and confirm:
   - Runtime: Docker
   - Dockerfile Path: `./Dockerfile`
   - Docker Build Context Directory: `.`
   - Health Check Path: `/api/health`
5. To provision the database from `render.yaml`, create/sync a Render Blueprint from this repository and review the proposed resources before applying. The Blueprint keeps the web service name `classbookings` and adds a new PostgreSQL database. If you are deploying only the code to the existing service, create a PostgreSQL database in Render Dashboard → New → PostgreSQL, then copy its **Internal Database URL** into `DATABASE_URL` (web service and database should be in the same region).
6. Open **Environment** and confirm these values exist:

   | Variable | Required value |
   |---|---|
   | `DATABASE_URL` | The Blueprint-managed PostgreSQL connection, or your existing persistent PostgreSQL internal connection string |
   | `SECRET_KEY` | Random secret at least 32 characters |
   | `ADMIN_EMAIL` | Your administrator login email |
   | `ADMIN_PASSWORD` | A strong, unique administrator password |

   Optional email settings: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`.

7. Save environment changes. If Render does not deploy automatically, choose **Manual Deploy → Deploy latest commit**.
8. Wait for the deploy to finish. The container starts FastAPI, checks `/api/health` (including the database connection), and only then starts Next.js.

## Important database note

This ZIP does not create a new database or migrate data from another database. Keep and use your existing persistent PostgreSQL database by copying its connection string into `DATABASE_URL`. Do not use SQLite for a public production deployment. Do not delete your existing database when replacing application files.

## Verify after deployment

- Public site: `https://classbookings.onrender.com/`
- Admin dashboard: `https://classbookings.onrender.com/admin`
- API health: `https://classbookings.onrender.com/api/health`

The health endpoint should return JSON similar to:

```json
{"status":"ok","database":"connected","capacity_per_session":25}
```

Then submit a test booking with a test email, confirm it appears in the admin dashboard as Pending, approve it, and check the public calendar/status lookup. Remove test data if you do not want it retained.

## Optional email setup

Configure valid SMTP credentials in Render Environment. Without SMTP configuration, booking data still saves, but the app will report that email delivery was not confirmed.

## Security and operational notes

- Keep all secrets in Render Environment, never in GitHub or this ZIP.
- The admin session token is held in the browser app state; sign out when finished.
- Before broad public use, add rate limiting, MFA, privacy/retention policy, monitoring, and tested database backup/restore procedures.
- This is an application starter and has not undergone an independent security audit.

## Local development

Backend dependencies: `pip install -r backend/requirements.txt`

Run backend with the required environment variables set, then run the frontend from `frontend/` using `npm install` and `npm run dev`. For the all-in-one Render container, leave `NEXT_PUBLIC_API_URL` unset so Next.js uses the local `/api/*` rewrite to FastAPI on `127.0.0.1:8000`.
