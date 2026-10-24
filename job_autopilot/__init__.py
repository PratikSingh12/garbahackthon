"""
Job Hunt Autopilot Package.
Track every application. Catch every fake offer.
"""

__version__ = "1.0.0"

from job_autopilot.models import (
    StageEnum,
    EmailMessage,
    ClassificationResult,
    ApplicationRecord,
    TrackerStats,
)
from job_autopilot.parser import load_inbox
from job_autopilot.classifier import classify_email
from job_autopilot.tracker import JobHuntTracker

__all__ = [
    "StageEnum",
    "EmailMessage",
    "ClassificationResult",
    "ApplicationRecord",
    "TrackerStats",
    "load_inbox",
    "classify_email",
    "JobHuntTracker",
]
