-- Royaltica Morning Class Booking PostgreSQL schema reference.
-- FastAPI/SQLAlchemy creates these tables and indexes automatically at startup.
CREATE TABLE IF NOT EXISTS bookings (
  id BIGSERIAL PRIMARY KEY, booking_reference VARCHAR(32) NOT NULL UNIQUE,
  class_date DATE NOT NULL, participant_name VARCHAR(160) NOT NULL,
  participant_email VARCHAR(320) NOT NULL, participant_phone VARCHAR(40),
  participant_note TEXT, status VARCHAR(20) NOT NULL DEFAULT 'Pending',
  created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
  reviewed_by VARCHAR(320), reviewed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_bookings_class_date ON bookings(class_date);
CREATE INDEX IF NOT EXISTS ix_bookings_participant_email ON bookings(participant_email);
CREATE INDEX IF NOT EXISTS ix_bookings_status ON bookings(status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_email_date ON bookings(participant_email, class_date) WHERE status IN ('Pending','Approved');
CREATE TABLE IF NOT EXISTS booking_audit (
  id BIGSERIAL PRIMARY KEY, booking_id BIGINT NOT NULL, action VARCHAR(20) NOT NULL,
  admin_email VARCHAR(320) NOT NULL, created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_booking_audit_booking_id ON booking_audit(booking_id);
