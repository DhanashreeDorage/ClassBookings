# Royaltica Publishing Morning Class Booking

Production-oriented single-service deployment for Render. The Next.js public portal and protected admin portal run in one Render web service; FastAPI runs privately inside the same container and is reverse-proxied through Next.js. Render PostgreSQL stores bookings persistently across devices.

## Features

- Public participant booking form and monthly calendar
- Daily 8:00–9:00 AM `America/New_York` sessions, daylight-saving aware
- Unlimited capacity and admin approval workflow
- Private booking lookup requiring booking reference plus registered email
- Public calendar exposes aggregate counts only
- Private `/admin` portal with server-validated bearer-token authentication
- Admin list includes student names, emails, phone numbers, notes, dates, and statuses
- Pending, Approved, Rejected, and Cancelled states
- SMTP notifications for request receipt and admin decisions (only reported as sent after SMTP succeeds)
- PostgreSQL persistent storage; no Google Calendar integration

## Deploy on Render (Blueprint)

1. Push this project to a GitHub repository you control.
2. In Render, choose **New → Blueprint** and select that repository.
3. Render reads `render.yaml` and provisions a PostgreSQL database and the web service.
4. When prompted, set `ADMIN_EMAIL` and a strong unique `ADMIN_PASSWORD`. Store the password in a password manager; do not commit it to Git.
5. Optionally provide SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`) to enable participant email notifications.
6. Deploy. Wait for the web service health check at `/api/health` to pass.
7. Open the service URL for participants. Open `<service-url>/admin` for the private admin login.

The blueprint generates `SECRET_KEY` and injects the managed PostgreSQL connection string. The API is bound to localhost inside the same container and is not separately exposed to the public internet. Next.js proxies `/api/*` to FastAPI on the internal loopback interface.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set SECRET_KEY (32+ random characters), ADMIN_EMAIL and ADMIN_PASSWORD
uvicorn app.main:app --reload
```

Frontend (in another terminal):

```bash
cd frontend
npm install
npm run dev
```

For local development, set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if you want direct API calls, or use the Next.js rewrite and run FastAPI on `127.0.0.1:8000`.

## Security and operational notes

- The public interface has no admin navigation link. `/admin` is protected by the API's admin login; knowing the URL does not grant access.
- Status lookup requires both the booking reference and matching email.
- Do not use demo credentials. Render prompts for your own admin credentials.
- Configure SMTP to enable real email. Without it, bookings still persist, but the app accurately reports that email delivery was not confirmed.
- Before broad public launch, add rate limiting (especially to login and public booking endpoints), MFA or an identity provider, a privacy notice, and a retention/deletion policy.
- Back up the managed database and test restoration.
- This app does not integrate Google Calendar.
