"""
SQLAlchemy ORM models for PostgreSQL — users and alerts.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from database.postgres import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user")  # admin | analyst | user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    log_id: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="")
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LogConfig(Base):
    __tablename__ = "log_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(128))           # e.g. "Custom App Log"
    log_path: Mapped[str] = mapped_column(String(512), unique=True)  # /var/log/custom.log
    collector_type: Mapped[str] = mapped_column(String(32))  # ssh|nginx|apache|mysql|docker|generic
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=True)  # FK → users.id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AlertInteraction(Base):
    __tablename__ = "alert_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(Integer, index=True)   # FK → alerts.id
    user_id: Mapped[int] = mapped_column(Integer)                # FK → users.id
    username: Mapped[str] = mapped_column(String(64))            # denormalized for display
    user_role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))              # "acknowledge" | "comment"
    message: Mapped[str] = mapped_column(Text, default="")       # comment body, empty for acks
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
