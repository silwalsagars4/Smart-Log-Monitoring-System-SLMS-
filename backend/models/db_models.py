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
    role: Mapped[str] = mapped_column(String(32), default="user")  # admin | user
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
