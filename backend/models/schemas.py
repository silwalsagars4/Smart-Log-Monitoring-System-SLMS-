"""
Pydantic schemas for request/response validation.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    password: str = Field(..., min_length=8)
    role: Optional[str] = "user"


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


# ── Logs ─────────────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    timestamp: str
    source: str
    event_type: Optional[str] = ""
    ip: Optional[str] = ""
    user: Optional[str] = ""
    method: Optional[str] = ""
    path: Optional[str] = ""
    status: Optional[int] = None
    message: str
    raw: Optional[str] = ""
    severity: Optional[str] = "information"
    anomaly_score: Optional[float] = 0.0
    is_anomaly: Optional[bool] = False
    human_insight: Optional[str] = ""
    ml_detail: Optional[dict] = None
    geo: Optional[dict] = None
    container: Optional[str] = ""

    class Config:
        populate_by_name = True


class LogIngest(BaseModel):
    """Schema for the direct ingestion endpoint."""
    timestamp: Optional[str] = None
    source: str
    message: str
    ip: Optional[str] = ""
    event_type: Optional[str] = ""
    raw: Optional[str] = ""
    extra: Optional[dict[str, Any]] = None


class LogsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[dict]


# ── Alerts ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    log_id: str
    severity: str
    source: str
    message: str
    ip: str
    anomaly_score: float
    acknowledged: bool
    notified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertInteractionOut(BaseModel):
    id: int
    alert_id: int
    username: str
    user_role: str
    action: str
    message: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


# ── Stats ─────────────────────────────────────────────────────────────────────

class SummaryStats(BaseModel):
    total_logs: int
    total_anomalies: int
    total_alerts: int
    severity_counts: dict[str, int]
    source_counts: dict[str, int]
    logs_per_minute: float
