# Upgrade notes

This bundle upgrades the existing Royaltica Morning Class Booking codebase. It does not create a second application or change the existing booking table schema.

## Changes
- Premium responsive public booking experience and admin dashboard.
- Next.js and React dependencies updated to current patched maintenance/LTS releases (Next.js 15.5.29, React 19.3.1).
- Public calendar with available-seat and pending/approved counts, without exposing participant details.
- Email + booking-reference status lookup (`ROY-000123`).
- Booking confirmation includes the reference.
- Admin sign-in uses `ADMIN_EMAIL` and `ADMIN_PASSWORD` from environment variables.
- Render single-container Docker deployment starts FastAPI and Next.js together and waits for the API health check.
- PostgreSQL URL normalization for Render's `postgres://` / `postgresql://` connection strings.
- Approval capacity locking enforces a maximum of 25 approved students per class date.

## Before deploying
1. Back up the existing Render PostgreSQL database.
2. Apply this bundle to the GitHub repository currently connected to the `classbookings` Render service.
3. Configure `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SECRET_KEY` (32+ characters), and `DATABASE_URL` in Render. Configure SMTP variables only if email notifications are to be sent.
4. Confirm the Render service builds from the repository root `Dockerfile`, and set health check path to `/health`.
5. Deploy and test calendar load, a pending booking, status lookup, admin login, approval at capacity, cancellation, and email delivery if SMTP is configured.

The archive can be prepared and statically checked here, but it cannot update the remote GitHub repository or Render service without access to that project. A full Next.js production build was not run in this environment because npm package installation did not complete.
