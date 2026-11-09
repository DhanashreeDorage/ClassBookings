import os
import smtplib
import logging
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Date, DateTime, Text, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("royaltica")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./royaltica.db")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
TZ = ZoneInfo("America/New_York")
CAPACITY = 25

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
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    learning_goal: str | None = Field(default=None, max_length=2000)

app = FastAPI(title="Royaltica Morning Publishing Class API", version="2.0.0")
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
    return {"status": "ok", "application": "royaltica-morning-class", "version": "2.0.0"}

@app.post("/api/admin/login")
def login(data: LoginIn):
    username = os.getenv("ADMIN_USERNAME", "admin")
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
        select(Booking.class_date, Booking.status, func.count(Booking.id))
        .where(Booking.class_date.between(start, end))
        .group_by(Booking.class_date, Booking.status)
    ).all()
    by_day: dict[str, dict[str, int]] = {}
    for class_day, status, count in rows:
        by_day.setdefault(class_day.isoformat(), {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0})
        by_day[class_day.isoformat()][status.lower()] = count
    sessions = []
    current = start
    while current <= end:
        counts = by_day.get(current.isoformat(), {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0})
        approved = counts["approved"]
        sessions.append({
            "date": current.isoformat(),
            "start_time": "08:00",
            "end_time": "09:00",
            "time_zone": "America/New_York",
            "approved": approved,
            "pending": counts["pending"],
            "capacity": CAPACITY,
            "available": max(0, CAPACITY - approved),
            "booking_status": "Full" if approved >= CAPACITY else "Open",
        })
        current += timedelta(days=1)
    return {"class_name": "Royaltica Morning Publishing Class", "schedule": "Daily", "sessions": sessions}

@app.post("/api/bookings")
def create_booking(data: BookingIn, session: Session = Depends(db)):
    if data.class_date < datetime.now(TZ).date():
        raise HTTPException(400, "Please choose today or a future class date")
    email = str(data.email).strip().lower()
    approved_count = session.scalar(
        select(func.count(Booking.id)).where(Booking.class_date == data.class_date, Booking.status == "Approved")
    ) or 0
    if approved_count >= CAPACITY:
        raise HTTPException(409, "This class is full. The maximum of 25 approved students has been reached.")
    duplicate = session.scalar(
        select(Booking).where(
            Booking.class_date == data.class_date,
            Booking.participant_email == email,
            Booking.status.in_(["Pending", "Approved"]),
        )
    )
    if duplicate:
        raise HTTPException(409, "An active booking already exists for this email and class date")
    booking = Booking(
        class_date=data.class_date,
        participant_name=data.full_name.strip(),
        participant_email=email,
        participant_phone=data.phone,
        learning_goal=data.learning_goal,
        status="Pending",
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)
    send_email(
        email,
        "Royaltica class booking request received",
        f"Hello {booking.participant_name},\n\nWe received your request for {booking.class_date:%B %d, %Y}, 8:00–9:00 AM Eastern Time.\nYour request is Pending. Pending requests do not reserve a seat; your seat is confirmed only after approval.\n\nRoyaltica Publishing",
    )
    admin_email = os.getenv("ADMIN_NOTIFICATION_EMAIL")
    if admin_email:
        send_email(
            admin_email,
            "New Morning Publishing Class booking request",
            f"New pending request #{booking.id}\nDate: {booking.class_date}\nName: {booking.participant_name}\nEmail: {booking.participant_email}",
        )
    return {"id": booking.id, "status": booking.status, "message": "Your request has been received. It is not confirmed until approved."}

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
                Booking.status == "Approved",
            )
        ) or 0
        if booking.status != "Approved" and approved_count >= CAPACITY:
            raise HTTPException(409, "This class is full. The maximum of 25 approved students has been reached.")
    booking.status = new_status
    booking.updated_at = datetime.now(timezone.utc)
    booking.reviewed_at = datetime.now(timezone.utc)
    booking.reviewed_by = admin
    session.commit()
    if new_status == "Approved":
        detail = f"Your booking for {booking.class_date:%B %d, %Y}, 8:00–9:00 AM Eastern Time is approved."
        subject = "Your Royaltica Morning Publishing Class booking is approved"
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
