import os
import smtplib
import logging
from datetime import date, datetime, timedelta, timezone, time
import re
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Date, DateTime, Text, select, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("royaltica")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./royaltica.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
IST = ZoneInfo("Asia/Kolkata")
ET = ZoneInfo("America/New_York")
TZ = IST
CAPACITY = 25
SLOT_STARTS = ["17:00", "18:00", "19:00", "20:00", "21:00"]

def slot_details(class_day: date, slot_start: str):
    start_hour, start_minute = map(int, slot_start.split(":"))
    start_ist = datetime.combine(class_day, time(start_hour, start_minute), tzinfo=IST)
    end_ist = start_ist + timedelta(hours=1)
    start_et = start_ist.astimezone(ET)
    end_et = end_ist.astimezone(ET)
    def fmt(value):
        return value.strftime("%-I:%M %p")
    et_day = start_et.strftime("%b %-d") if start_et.date() != class_day else "same day"
    return {
        "start_ist": fmt(start_ist), "end_ist": fmt(end_ist),
        "start_et": fmt(start_et), "end_et": fmt(end_et),
        "et_date_label": et_day,
        "ist_label": f"{fmt(start_ist)}–{fmt(end_ist)} IST",
        "et_label": f"{fmt(start_et)}–{fmt(end_et)} {start_et.tzname()}",
    }

if len(SECRET_KEY) < 32:
    raise RuntimeError("Set SECRET_KEY to a random value of at least 32 characters in Render environment variables")

engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_date: Mapped[date] = mapped_column(Date, index=True)
    slot_start: Mapped[str | None] = mapped_column(String(5), nullable=True, index=True)
    participant_name: Mapped[str] = mapped_column(String(160))
    participant_email: Mapped[str] = mapped_column(String(254), index=True)
    participant_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

class ClassSession(Base):
    __tablename__ = "class_sessions"
    class_date: Mapped[date] = mapped_column(Date, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)
# Backward-compatible migration for existing Render PostgreSQL/SQLite databases.
with engine.begin() as connection:
    columns = {col["name"] for col in __import__("sqlalchemy").inspect(engine).get_columns("bookings")}
    if "slot_start" not in columns:
        connection.execute(text("ALTER TABLE bookings ADD COLUMN slot_start VARCHAR(5) NULL"))

def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def send_email(to: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        log.warning("SMTP not configured; email not sent to %s (%s)", to, subject)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_FROM", "Royaltica Publishing <no-reply@example.com>")
    msg["To"] = to
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as server:
            server.starttls()
            if os.getenv("SMTP_USERNAME"):
                server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD", ""))
            server.send_message(msg)
        return True
    except Exception:
        log.exception("Email delivery failed")
        return False

def admin_token(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Administrator login required")
    try:
        payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(403, "Administrator access required")
        return payload.get("sub", "admin")
    except JWTError:
        raise HTTPException(401, "Invalid or expired administrator session")

class LoginIn(BaseModel):
    username: str
    password: str

class BookingIn(BaseModel):
    class_date: date
    slot_start: str
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    learning_goal: str | None = Field(default=None, max_length=2000)

app = FastAPI(title="Royaltica Evening Publishing Class API", version="3.0.0")
origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.on_event("startup")
def provision_admin():
    if not os.getenv("ADMIN_PASSWORD"):
        log.warning("ADMIN_PASSWORD is unset; admin login is disabled")
    else:
        log.info("Royaltica booking API ready; admin username configured")

@app.get("/health")
def health():
    return {"status": "ok", "application": "royaltica-evening-class", "version": "3.0.0"}

@app.post("/api/admin/login")
def login(data: LoginIn):
    username = os.getenv("ADMIN_EMAIL") or os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD")
    if not password or data.username != username or data.password != password:
        raise HTTPException(401, "Incorrect username or password")
    token = jwt.encode(
        {"sub": username, "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"access_token": token, "token_type": "bearer", "expires_in": 28800}

@app.get("/api/public/calendar")
def public_calendar(start: date = Query(...), end: date = Query(...), session: Session = Depends(db)):
    if end < start or (end - start).days > 366:
        raise HTTPException(400, "Choose a date range up to 366 days")
    rows = session.execute(
        select(Booking.class_date, Booking.slot_start, Booking.status, func.count(Booking.id))
        .where(Booking.class_date.between(start, end))
        .group_by(Booking.class_date, Booking.slot_start, Booking.status)
    ).all()
    grouped: dict[tuple[str, str], dict[str, int]] = {}
    legacy_by_day: dict[str, dict[str, int]] = {}
    for class_day, slot_start, status, count in rows:
        if slot_start is None:
            legacy_by_day.setdefault(class_day.isoformat(), {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0})
            legacy_by_day[class_day.isoformat()][status.lower()] = count
            continue
        key = (class_day.isoformat(), slot_start)
        grouped.setdefault(key, {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0})
        grouped[key][status.lower()] = count

    participant_rows = session.execute(
        select(Booking.class_date, Booking.slot_start, Booking.participant_name)
        .where(
            Booking.class_date.between(start, end),
            Booking.status == "Approved",
        )
        .order_by(Booking.class_date, Booking.slot_start, Booking.participant_name)
    ).all()
    names_by_slot: dict[tuple[str, str], list[str]] = {}
    legacy_names_by_day: dict[str, list[str]] = {}
    for class_day, slot_start, participant_name in participant_rows:
        if slot_start is None:
            legacy_names_by_day.setdefault(class_day.isoformat(), []).append(participant_name)
        else:
            names_by_slot.setdefault((class_day.isoformat(), slot_start), []).append(participant_name)

    sessions = []
    current = start
    while current <= end:
        day_key = current.isoformat()
        slots = []
        for slot_start in SLOT_STARTS:
            counts = grouped.get((day_key, slot_start), {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0})
            details = slot_details(current, slot_start)
            approved = counts["approved"]
            slots.append({
                "slot_start": slot_start,
                **details,
                "approved": approved,
                "pending": counts["pending"],
                "participants": names_by_slot.get((day_key, slot_start), []),
                "capacity": CAPACITY,
                "available": max(0, CAPACITY - approved),
                "full": approved >= CAPACITY,
            })
        legacy_counts = legacy_by_day.get(day_key, {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0})
        legacy = None
        if any(legacy_counts.values()):
            legacy = {
                "label": "Previous schedule · 8:00–9:00 AM US Eastern",
                "pending": legacy_counts["pending"],
                "approved": legacy_counts["approved"],
                "participants": legacy_names_by_day.get(day_key, []),
            }
        sessions.append({
            "date": day_key,
            "slots": slots,
            "legacy": legacy,
            "pending": sum(slot["pending"] for slot in slots) + legacy_counts["pending"],
            "approved": sum(slot["approved"] for slot in slots) + legacy_counts["approved"],
            "booking_status": "Full" if all(slot["full"] for slot in slots) else "Open",
        })
        current += timedelta(days=1)
    return {
        "class_name": "Royaltica Evening Publishing Class",
        "schedule": "Daily, 5:00 PM–10:00 PM IST",
        "time_zone": "Asia/Kolkata",
        "converted_time_zone": "America/New_York",
        "sessions": sessions,
    }

@app.post("/api/bookings")
def create_booking(data: BookingIn, session: Session = Depends(db)):
    if data.class_date < datetime.now(IST).date():
        raise HTTPException(400, "Please choose today or a future class date")
    if data.slot_start not in SLOT_STARTS:
        raise HTTPException(400, "Choose an available one-hour slot between 5:00 PM and 10:00 PM IST")
    email = str(data.email).strip().lower()
    if engine.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"),
            {"email": email},
        )
    existing_active = session.scalar(
        select(Booking).where(
            Booking.participant_email == email,
            Booking.status.in_(["Pending", "Approved"]),
        )
    )
    if existing_active:
        raise HTTPException(
            409,
            f"You already have an active booking for {existing_active.class_date:%B %d, %Y} ({existing_active.status}). Only one active booking is allowed per person. Please check your approval status instead.",
        )
    approved_count = session.scalar(
        select(func.count(Booking.id)).where(
            Booking.class_date == data.class_date,
            Booking.slot_start == data.slot_start,
            Booking.status == "Approved",
        )
    ) or 0
    if approved_count >= CAPACITY:
        raise HTTPException(409, "This time slot is full. Please choose another slot.")
    booking = Booking(
        class_date=data.class_date,
        slot_start=data.slot_start,
        participant_name=data.full_name.strip(),
        participant_email=email,
        participant_phone=data.phone,
        learning_goal=data.learning_goal,
        status="Pending",
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)
    booking_reference = f"ROY-{booking.id:06d}"
    details = slot_details(booking.class_date, booking.slot_start)
    send_email(
        email,
        "Royaltica publishing class booking request received",
        f"Hello {booking.participant_name},\n\nWe received your request for {booking.class_date:%B %d, %Y}.\nIndia time: {details['ist_label']}\nUS Eastern time: {details['et_label']} ({details['et_date_label']})\nBooking reference: {booking_reference}\nYour request is Pending. Your slot is confirmed only after approval.\n\nUse your email address and booking reference to check your status.\n\nRoyaltica Publishing",
    )
    admin_email = os.getenv("ADMIN_NOTIFICATION_EMAIL")
    if admin_email:
        send_email(
            admin_email,
            "New Royaltica Publishing Class booking request",
            f"New pending request #{booking.id}\nDate: {booking.class_date}\nIndia time: {details['ist_label']}\nUS Eastern time: {details['et_label']}\nName: {booking.participant_name}\nEmail: {booking.participant_email}",
        )
    return {
        "id": booking.id,
        "reference": booking_reference,
        "status": booking.status,
        "ist_time": details["ist_label"],
        "eastern_time": details["et_label"],
        "message": "Your request has been received. It is not confirmed until approved.",
    }

@app.get("/api/bookings/status")
def booking_status(email: EmailStr, reference: str, session: Session = Depends(db)):
    """Return only the status for a matching email + booking reference."""
    match = re.fullmatch(r"ROY-(\d{1,10})", reference.strip().upper())
    if not match:
        raise HTTPException(400, "Enter a valid booking reference, for example ROY-000123")
    booking_id = int(match.group(1))
    booking = session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.participant_email == str(email).strip().lower())
    )
    if not booking:
        raise HTTPException(404, "No booking matches that email address and reference")
    details = slot_details(booking.class_date, booking.slot_start) if booking.slot_start else None
    return {
        "reference": f"ROY-{booking.id:06d}",
        "class_date": booking.class_date.isoformat(),
        "class_time": (details["ist_label"] + " / " + details["et_label"]) if details else "Previous schedule: 8:00–9:00 AM US Eastern",
        "ist_time": details["ist_label"] if details else "Previous schedule",
        "eastern_time": details["et_label"] if details else "8:00–9:00 AM US Eastern",
        "status": booking.status,
        "message": "Your seat is confirmed." if booking.status == "Approved" else "Your request is awaiting review." if booking.status == "Pending" else "Please contact Royaltica Publishing if you need help with this request.",
    }

@app.get("/api/admin/bookings")
def list_bookings(
    status: str | None = None,
    class_date: date | None = None,
    q: str | None = None,
    admin=Depends(admin_token),
    session: Session = Depends(db),
):
    query = select(Booking).order_by(Booking.class_date.desc(), Booking.created_at.desc())
    if status and status != "All":
        if status not in ["Pending", "Approved", "Rejected", "Cancelled"]:
            raise HTTPException(400, "Invalid status")
        query = query.where(Booking.status == status)
    if class_date:
        query = query.where(Booking.class_date == class_date)
    if q:
        term = f"%{q.strip()}%"
        query = query.where((Booking.participant_name.ilike(term)) | (Booking.participant_email.ilike(term)))
    return [
        {
            "id": b.id,
            "class_date": b.class_date.isoformat(),
            "slot_start": b.slot_start,
            "ist_time": slot_details(b.class_date, b.slot_start)["ist_label"] if b.slot_start else "Previous schedule",
            "eastern_time": slot_details(b.class_date, b.slot_start)["et_label"] if b.slot_start else "8:00–9:00 AM US Eastern",
            "name": b.participant_name,
            "email": b.participant_email,
            "phone": b.participant_phone,
            "learning_goal": b.learning_goal,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in session.scalars(query).all()
    ]

def lock_session_date(class_date: date, session: Session):
    """Serialize approval decisions for the same class date on PostgreSQL."""
    row = session.get(ClassSession, class_date)
    if row is None:
        try:
            session.add(ClassSession(class_date=class_date))
            session.commit()
        except IntegrityError:
            session.rollback()
    statement = select(ClassSession).where(ClassSession.class_date == class_date).with_for_update()
    return session.scalar(statement)

def update_status(booking_id: int, new_status: str, admin: str, session: Session):
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status in ["Rejected", "Cancelled"]:
        raise HTTPException(409, "This booking is no longer active")
    if booking.status == "Approved" and new_status == "Approved":
        return {"id": booking.id, "status": booking.status, "message": "Booking is already approved"}
    if new_status == "Approved":
        lock_session_date(booking.class_date, session)
        session.refresh(booking)
        approved_count = session.scalar(
            select(func.count(Booking.id)).where(
                Booking.class_date == booking.class_date,
                Booking.slot_start == booking.slot_start,
                Booking.status == "Approved",
            )
        ) or 0
        if booking.status != "Approved" and approved_count >= CAPACITY:
            raise HTTPException(409, "This time slot is full. Please review another slot.")
    booking.status = new_status
    booking.updated_at = datetime.now(timezone.utc)
    booking.reviewed_at = datetime.now(timezone.utc)
    booking.reviewed_by = admin
    session.commit()
    slot_info = slot_details(booking.class_date, booking.slot_start) if booking.slot_start else None
    if new_status == "Approved":
        timing = f"India time: {slot_info['ist_label']}. US Eastern time: {slot_info['et_label']}." if slot_info else "This booking is under the previous 8:00–9:00 AM US Eastern schedule."
        detail = f"Your booking for {booking.class_date:%B %d, %Y} is approved. {timing}"
        subject = "Your Royaltica Publishing Class booking is approved"
    elif new_status == "Rejected":
        detail = f"Your booking request for {booking.class_date:%B %d, %Y} was not approved."
        subject = "Update on your Royaltica class booking"
    else:
        detail = f"Your booking for {booking.class_date:%B %d, %Y} has been cancelled."
        subject = "Your Royaltica class booking was cancelled"
    send_email(booking.participant_email, subject, f"Hello {booking.participant_name},\n\n{detail}\n\nRoyaltica Publishing")
    return {"id": booking.id, "status": booking.status, "message": "Booking status updated"}

@app.post("/api/admin/bookings/{booking_id}/approve")
def approve(booking_id: int, admin=Depends(admin_token), session: Session = Depends(db)):
    return update_status(booking_id, "Approved", admin, session)

@app.post("/api/admin/bookings/{booking_id}/reject")
def reject(booking_id: int, admin=Depends(admin_token), session: Session = Depends(db)):
    return update_status(booking_id, "Rejected", admin, session)

@app.post("/api/admin/bookings/{booking_id}/cancel")
def cancel(booking_id: int, admin=Depends(admin_token), session: Session = Depends(db)):
    return update_status(booking_id, "Cancelled", admin, session)
