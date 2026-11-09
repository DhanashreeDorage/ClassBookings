import hmac
import secrets
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Date, DateTime, Index, String, Text, create_engine, func, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

EASTERN = ZoneInfo("America/New_York")


class Settings(BaseSettings):
    database_url: str = "sqlite:///./royaltica.db"  # Local development only; use PostgreSQL in production.
    secret_key: str = ""
    admin_email: str = ""
    admin_password: str = ""
    frontend_origin: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
if not settings.secret_key or len(settings.secret_key) < 32:
    raise RuntimeError("Set SECRET_KEY to a random value of at least 32 characters in backend/.env")
if not settings.admin_email or not settings.admin_password:
    raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD in backend/.env")

# Render supplies PostgreSQL URLs as postgres:// or postgresql://. SQLAlchemy uses
# the explicit psycopg v3 dialect installed in requirements.txt.
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    class_date: Mapped[date] = mapped_column(Date, index=True)
    participant_name: Mapped[str] = mapped_column(String(160))
    participant_email: Mapped[str] = mapped_column(String(320), index=True)
    participant_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    participant_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Audit(Base):
    __tablename__ = "booking_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(20))
    admin_email: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


Index(
    "uq_active_email_date", Booking.participant_email, Booking.class_date,
    unique=True,
    postgresql_where=text("status IN ('Pending', 'Approved')"),
    sqlite_where=text("status IN ('Pending', 'Approved')"),
)
Base.metadata.create_all(engine)

app = FastAPI(title="Royaltica Morning Class Booking API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


class BookingCreate(BaseModel):
    class_date: date
    participant_name: str = Field(min_length=2, max_length=160)
    participant_email: EmailStr
    participant_phone: str | None = Field(default=None, max_length=40)
    participant_note: str | None = Field(default=None, max_length=2000)


class StatusUpdate(BaseModel):
    status: str


class StatusLookup(BaseModel):
    booking_reference: str = Field(min_length=8, max_length=32)
    participant_email: EmailStr


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def admin_from_token(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        email = payload.get("sub")
        if email != settings.admin_email:
            raise ValueError()
        return email
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired admin session", headers={"WWW-Authenticate": "Bearer"})


def notify(to: str, subject: str, body: str) -> bool:
    if not (settings.smtp_host and settings.smtp_from):
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/admin/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    valid_email = hmac.compare_digest(form.username.lower(), settings.admin_email.lower())
    valid_password = hmac.compare_digest(form.password, settings.admin_password)
    if not (valid_email and valid_password):
        raise HTTPException(status_code=401, detail="Incorrect admin email or password")
    token = jwt.encode(
        {"sub": settings.admin_email, "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        settings.secret_key,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/bookings")
def create_booking(payload: BookingCreate, db: Session = Depends(db_session)):
    if payload.class_date < datetime.now(EASTERN).date():
        raise HTTPException(400, "Please choose today or a future class date")
    email = str(payload.participant_email).lower()
    existing = db.scalar(select(Booking).where(
        Booking.participant_email == email,
        Booking.class_date == payload.class_date,
        Booking.status.in_(["Pending", "Approved"]),
    ))
    if existing:
        raise HTTPException(409, "An active request already exists for this email and class date")

    reference = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16].upper()
    booking = Booking(
        booking_reference=reference,
        class_date=payload.class_date,
        participant_name=payload.participant_name.strip(),
        participant_email=email,
        participant_phone=payload.participant_phone,
        participant_note=payload.participant_note,
        status="Pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    delivered = notify(
        email,
        "Royaltica Morning Publishing Class — request received",
        f"Hello {booking.participant_name},\n\nWe received your request for {booking.class_date}. Your request is Pending and is not confirmed until approved by an administrator.\n\nYour private booking reference is: {reference}\nTo check your status, visit the booking status page and enter this reference and your email address.\n\nClass time: 8:00–9:00 AM Eastern Time.\n\nRoyaltica Publishing",
    )
    return {
        "id": booking.id,
        "booking_reference": reference,
        "status": booking.status,
        "class_date": booking.class_date,
        "email_notification_sent": delivered,
        "message": "Request recorded as Pending. It is not confirmed until approved.",
    }


@app.post("/api/bookings/status")
def booking_status(payload: StatusLookup, db: Session = Depends(db_session)):
    email = str(payload.participant_email).lower()
    booking = db.scalar(select(Booking).where(
        Booking.booking_reference == payload.booking_reference.strip().upper(),
        Booking.participant_email == email,
    ))
    if not booking:
        raise HTTPException(status_code=404, detail="No booking matched those details")
    return {
        "booking_reference": booking.booking_reference,
        "class_date": booking.class_date,
        "class_time": "8:00–9:00 AM",
        "time_zone": "America/New_York",
        "status": booking.status,
        "updated_at": booking.updated_at,
    }


@app.get("/api/calendar")
def public_calendar(start: date, end: date, db: Session = Depends(db_session)):
    if end < start or (end - start).days > 400:
        raise HTTPException(400, "Date range must be 1–400 days")
    rows = db.execute(
        select(Booking.class_date, Booking.status, func.count(Booking.id))
        .where(Booking.class_date.between(start, end))
        .group_by(Booking.class_date, Booking.status)
    ).all()
    result = {}
    for day, status_value, count in rows:
        result.setdefault(day.isoformat(), {"pending": 0, "approved": 0})
        if status_value in {"Pending", "Approved"}:
            result[day.isoformat()][status_value.lower()] = count
    return {"time": "8:00 AM–9:00 AM", "time_zone": "America/New_York", "capacity": "Unlimited", "dates": result}


@app.get("/api/admin/bookings")
def list_bookings(
    status_filter: str | None = None,
    class_date: date | None = None,
    q: str | None = None,
    db: Session = Depends(db_session),
    admin: str = Depends(admin_from_token),
):
    stmt = select(Booking).order_by(Booking.class_date, Booking.created_at)
    if status_filter and status_filter != "All":
        stmt = stmt.where(Booking.status == status_filter)
    if class_date:
        stmt = stmt.where(Booking.class_date == class_date)
    if q:
        stmt = stmt.where((Booking.participant_name.ilike(f"%{q}%")) | (Booking.participant_email.ilike(f"%{q}%")))
    return [
        {"id": b.id, "class_date": b.class_date, "name": b.participant_name, "email": b.participant_email,
         "phone": b.participant_phone, "note": b.participant_note, "status": b.status,
         "created_at": b.created_at, "reviewed_at": b.reviewed_at, "reviewed_by": b.reviewed_by}
        for b in db.scalars(stmt).all()
    ]


@app.patch("/api/admin/bookings/{booking_id}")
def update_booking(
    booking_id: int,
    payload: StatusUpdate,
    db: Session = Depends(db_session),
    admin: str = Depends(admin_from_token),
):
    if payload.status not in {"Approved", "Rejected", "Cancelled"}:
        raise HTTPException(400, "Status must be Approved, Rejected, or Cancelled")
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if payload.status == "Cancelled" and booking.status != "Approved":
        raise HTTPException(409, "Only approved bookings can be cancelled")
    if booking.status not in {"Pending", "Approved"}:
        raise HTTPException(409, "This booking has already been closed")
    booking.status = payload.status
    booking.updated_at = datetime.now(timezone.utc)
    booking.reviewed_at = booking.updated_at
    booking.reviewed_by = admin
    db.add(Audit(booking_id=booking.id, action=payload.status, admin_email=admin))
    db.commit()
    db.refresh(booking)
    delivered = notify(
        booking.participant_email,
        f"Royaltica Morning Publishing Class — booking {payload.status.lower()}",
        f"Hello {booking.participant_name},\n\nYour booking request for {booking.class_date} has been {payload.status.lower()}.\n\nClass time: 8:00–9:00 AM Eastern Time.\nBooking reference: {booking.booking_reference}\n\nRoyaltica Publishing",
    )
    return {"id": booking.id, "status": booking.status, "email_notification_sent": delivered}
