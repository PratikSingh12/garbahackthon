"""
Data models for Job Hunt Autopilot.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StageEnum(str, Enum):
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
    SCAM = "scam"


class EmailMessage(BaseModel):
    id: str
    sender: str
    sender_email: str = ""
    sender_domain: str = ""
    recipient: str = ""
    subject: str
    date: datetime
    body: str


class ScamAnalysis(BaseModel):
    is_scam: bool = False
    risk_score: float = 0.0  # 0.0 to 1.0
    reasons: List[str] = Field(default_factory=list)
    signals_detected: List[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    email_id: str
    stage: StageEnum
    company: str
    role: str
    confidence: float
    scam_analysis: ScamAnalysis
    summary: str


class ApplicationRecord(BaseModel):
    id: str
    company: str
    role: str
    current_stage: StageEnum
    application_date: datetime
    last_update_date: datetime
    days_elapsed: int
    follow_up_due: bool
    follow_up_reason: Optional[str] = None
    follow_up_template: Optional[str] = None
    is_scam: bool = False
    scam_reasons: List[str] = Field(default_factory=list)
    latest_subject: str
    sender: str
    sender_email: str = ""
    raw_body: str = ""
    history: List[Dict[str, Any]] = Field(default_factory=list)


class TrackerStats(BaseModel):
    total_emails: int = 0
    total_applications: int = 0
    stage_counts: Dict[str, int] = Field(default_factory=dict)
    scams_flagged: int = 0
    follow_ups_due: int = 0
    offers_received: int = 0
    interviews_scheduled: int = 0
    rejections_count: int = 0
