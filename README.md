# Royaltica Publishing Morning Class Booking — corrected deployment package

A two-interface booking app: public booking page + public calendar, and a protected admin dashboard. The app runs Next.js and FastAPI in one Render Docker web service and stores records in PostgreSQL.

## Included behavior

- Daily 8:00–9:00 AM `America/New_York` session (automatically follows Eastern daylight saving time)
- Maximum 25 active bookings per date; Pending and Approved requests reserve a place
- Admin approval required; statuses are Pending, Approved, Rejected, and Cancelled
- Public calendar shows aggregate counts only; no participant names, email addresses, phone numbers, or notes
- Admin dashboard shows participant details and supports approval, rejection, and cancellation
- Participants can look up their booking using booking reference + registered email
- Duplicate active requests for the same email/date are blocked
- PostgreSQL persistence; no Google Calendar integration
- Optional email notifications; the UI reports success only when SMTP delivery succeeds
- Backend/database health check must pass before the frontend starts

## Deploy to Render using Neon Free PostgreSQL

This package uses Render's free web service and Neon PostgreSQL. Neon is a separate database provider; the database connection string is supplied to Render as an environment variable.

1. Create a PostgreSQL project on Neon Free and copy its connection string. Keep `sslmode=require` in the URL. Treat the URL as a password.
2. Upload these project files to a GitHub repository you control. `render.yaml` must be at the repository root.
3. In Render, select **New → Blueprint**, connect that repository, and apply the Blueprint.
4. When prompted, enter `DATABASE_URL` (the Neon connection string), `ADMIN_EMAIL`, and a strong unique `ADMIN_PASSWORD`. Render generates `SECRET_KEY` automatically.
5. Wait until the deploy succeeds and `/api/health` passes.
6. Open the Render service URL for the public booking page. Open `<service-url>/admin` for administrator sign-in.

### Updating your existing `classbookings.onrender.com` service

If you want to keep the current Render service and URL, update the GitHub repository connected to that service with the files in this package, then trigger **Manual Deploy → Deploy latest commit**. Do not create a second Render service unless you want a new URL.

In the existing Render service, open **Environment** and verify these variables exist:

- `DATABASE_URL`: your Neon PostgreSQL connection string (or another persistent PostgreSQL URL)
- `SECRET_KEY`: a random secret of at least 32 characters
- `ADMIN_EMAIL`: the admin login email
- `ADMIN_PASSWORD`: a strong, unique admin password

To generate a secret locally, run:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into Render as `SECRET_KEY`. Do not put secrets in GitHub or share them in chat. Save the variables and redeploy.

## Admin and participant URLs

- Public booking page: `https://YOUR-SERVICE.onrender.com/`
- Admin dashboard: `https://YOUR-SERVICE.onrender.com/admin`
- Health check: `https://YOUR-SERVICE.onrender.com/api/health`

The health check returns `status: ok`, `database: connected`, and the configured per-session capacity only when the API and database are reachable.

## Optional email notifications

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM` in Render. Render Free may restrict outbound SMTP ports; use an email provider/API that supports HTTPS or an eligible paid hosting option if SMTP cannot connect. Without working email configuration, booking records still save and the app explicitly says email delivery was not confirmed.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

For local development, `backend/.env` must contain `SECRET_KEY` (32+ characters), `ADMIN_EMAIL`, and `ADMIN_PASSWORD`. The example SQLite database is for local testing only; use persistent PostgreSQL for deployment.

## Important launch notes

- This is an operational starter app, not a fully audited enterprise booking platform. Before broad public use, add rate limiting, MFA, a privacy notice, a retention/deletion policy, and a tested database backup/restore process.
- Render Free services can sleep when idle; the first visit may take time to wake. Neon Free also has usage limits and may scale compute to zero.
- Keep the admin password and database connection string private.
