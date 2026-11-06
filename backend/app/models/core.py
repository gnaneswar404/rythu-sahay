import enum
import secrets
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CaseStatus(str, enum.Enum):
    NEW = "NEW"
    INFORMATION_REQUIRED = "INFORMATION_REQUIRED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ASSIGNED = "ASSIGNED"
    GUIDANCE_PROVIDED = "GUIDANCE_PROVIDED"
    FOLLOW_UP_PENDING = "FOLLOW_UP_PENDING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    username: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    village: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    mandal: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    profile_photo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    profile_photo_media_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allow_phone_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    district: Mapped[str] = mapped_column(String(120), default="Nalgonda")
    preferred_language: Mapped[str] = mapped_column(String(20), default="te")
    consent_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cases: Mapped[list["Case"]] = relationship(back_populates="farmer", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="farmer", cascade="all, delete-orphan")


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_status_severity", "status", "severity"),
        Index("ix_cases_location", "village", "mandal"),
    )

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    crop: Mapped[str] = mapped_column(String(40), default="cotton")
    village: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    mandal: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    district: Mapped[str] = mapped_column(String(120), default="Nalgonda")
    problem_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.MEDIUM)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.NEW, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    farmer_access_token: Mapped[str] = mapped_column(String(100), unique=True, index=True, default=lambda: secrets.token_urlsafe(24))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    farmer: Mapped[Farmer] = relationship(back_populates="cases")
    actions: Mapped[list["CaseAction"]] = relationship(back_populates="case", cascade="all, delete-orphan", order_by="CaseAction.created_at")
    followups: Mapped[list["Followup"]] = relationship(back_populates="case", cascade="all, delete-orphan", order_by="Followup.scheduled_date")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseAction(Base):
    __tablename__ = "case_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    expert_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="actions")


class Followup(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    scheduled_date: Mapped[date] = mapped_column(Date)
    farmer_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="followups")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int | None] = mapped_column(ForeignKey("farmers.id"), nullable=True, index=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(Text)
    speaker: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    farmer: Mapped[Farmer | None] = relationship(back_populates="conversations")
    case: Mapped[Case | None] = relationship(back_populates="conversations")


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(16), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    village: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mandal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    profile_photo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    profile_photo_media_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allow_phone_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    skills: Mapped[str] = mapped_column(Text, default="")
    daily_wage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FarmerAccount(Base):
    __tablename__ = "farmer_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), unique=True, index=True)
    farmer: Mapped[Farmer] = relationship()


class MarketJob(Base):
    __tablename__ = "market_jobs"
    __table_args__ = (
        Index("ix_market_jobs_work_date_status", "work_date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    village: Mapped[str] = mapped_column(String(120))
    mandal: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    required_workers: Mapped[int] = mapped_column(Integer, default=1)
    daily_wage: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    farmer: Mapped[Farmer] = relationship()


class MarketTeam(Base):
    __tablename__ = "market_teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["MarketTeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", order_by="MarketTeamMember.id"
    )


class MarketTeamMember(Base):
    __tablename__ = "market_team_members"
    __table_args__ = (UniqueConstraint("team_id", "worker_id", name="uq_market_team_worker"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("market_teams.id"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    team: Mapped[MarketTeam] = relationship(back_populates="members")
    worker: Mapped[Worker] = relationship()


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("job_id", "worker_id", name="uq_job_application_worker"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("market_jobs.id"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("market_teams.id"), nullable=True)
    proposed_wage: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="NEGOTIATING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[MarketJob] = relationship()
    worker: Mapped[Worker] = relationship()
    team: Mapped[MarketTeam | None] = relationship()


class JobBooking(Base):
    __tablename__ = "job_bookings"
    __table_args__ = (
        UniqueConstraint("application_id", "worker_id", name="uq_booking_application_worker"),
        Index(
            "uq_worker_active_booking_date",
            "worker_id",
            "work_date",
            unique=True,
            sqlite_where=text("status IN ('PENDING', 'CONFIRMED')"),
            postgresql_where=text("status IN ('PENDING', 'CONFIRMED')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("job_applications.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("market_jobs.id"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    agreed_wage: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    application: Mapped[JobApplication] = relationship()
    job: Mapped[MarketJob] = relationship()
    worker: Mapped[Worker] = relationship()
    messages: Mapped[list["JobBookingMessage"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", order_by="JobBookingMessage.created_at"
    )


class JobBookingMessage(Base):
    __tablename__ = "job_booking_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("job_bookings.id", ondelete="CASCADE"), index=True)
    sender_type: Mapped[str] = mapped_column(String(12))
    sender_id: Mapped[int] = mapped_column(Integer)
    sender_name: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booking: Mapped[JobBooking] = relationship(back_populates="messages")
