# Upgrade notes

This bundle updates the existing Royaltica class-booking application to support evening time-slot selection.

## Schedule and booking rules
- Five one-hour slots each day: 5:00–6:00 PM, 6:00–7:00 PM, 7:00–8:00 PM, 8:00–9:00 PM, and 9:00–10:00 PM India Standard Time (IST).
- Each slot also displays its automatically converted US Eastern time (EST or EDT), calculated for the selected date so daylight-saving changes are handled.
- One active booking per email address across all dates. Rejected or cancelled requests do not block a new booking.
- New requests start Pending. Only Approved bookings count against the 25-person capacity for each one-hour slot.
- Public calendar shows approved participant names and their selected IST slot, plus pending counts. It does not expose email addresses or phone numbers.
- Existing bookings from the previous fixed 8:00–9:00 AM US Eastern schedule remain visible as previous-schedule records; they are not silently assigned to a new evening slot.

## Application updates
- Simple responsive public booking page and admin dashboard.
- Public calendar, booking form, approval-status lookup, admin approve/reject/cancel workflow.
- PostgreSQL persistence and backward-compatible nullable `slot_start` database migration.
- Optional SMTP notifications; delivery requires SMTP configuration.
- Render single-container Docker deployment starts FastAPI and Next.js together and waits for the API health check.

## Before deploying
1. Back up the existing Render PostgreSQL database.
2. Apply this bundle to the GitHub repository currently connected to the `classbookings` Render service.
3. Configure `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SECRET_KEY` (32+ characters), and `DATABASE_URL` in Render. Configure SMTP variables only if email notifications are required.
4. Confirm the Render service builds from the repository-root `Dockerfile`, and set health check path to `/health`.
5. Deploy and test each IST slot, Eastern-time conversion in both EST and EDT periods, one-active-booking-per-email, pending/approval status, capacity per slot, and cancellation.

The package passed Python syntax and ZIP integrity checks. A full Next.js production build was not verified because npm dependency installation timed out in this environment. The remote GitHub repository and Render service have not been changed by creating this archive.
