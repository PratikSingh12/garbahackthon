"""
Self-updating application tracker with 7-day follow-up reminder engine.
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from job_autopilot.models import (
    EmailMessage,
    ClassificationResult,
    ApplicationRecord,
    TrackerStats,
    StageEnum,
)
from job_autopilot.classifier import classify_email


def generate_follow_up_template(company: str, role: str, days_elapsed: int) -> str:
    """Generate a polite, professional, high-converting follow-up email draft."""
    return f"""Subject: Following up on application: {role} - Alex Chen

Hi {company} Recruiting Team,

I hope you are having a great week!

I recently submitted my application for the {role} position ({days_elapsed} days ago) and wanted to briefly reiterate my strong interest in joining {company}.

Having recently led distributed infrastructure initiatives in my prior role, I am particularly excited about {company}'s engineering challenges and would love the opportunity to contribute to your team.

Please let me know if there are any additional materials, portfolio links, or references I can provide to support my application.

Thank you very much for your time and consideration.

Warm regards,
Alex Chen
Senior Software Engineer
linkedin.com/in/alexchen-demo | (555) 019-2834"""


class JobHuntTracker:
    """
    Core tracker engine that processes inbox emails, categorizes pipeline stages,
    flags scams in red with reasons, and computes 7-day follow-up reminders.
    """

    def __init__(self, reference_date: Optional[datetime] = None):
        """
        reference_date: datetime to calculate elapsed days from.
        If None, will use the latest email's timestamp or current time.
        """
        self.reference_date = reference_date
        self.records: Dict[str, ApplicationRecord] = {}
        self.raw_results: List[ClassificationResult] = []

    def process_emails(self, emails: List[EmailMessage]) -> List[ApplicationRecord]:
        """Process a batch of emails through the unified classification pipeline."""
        if not emails:
            return []

        # Determine reference date if not provided (default to latest email date in sample)
        if not self.reference_date:
            latest_email_date = max(e.date for e in emails)
            self.reference_date = latest_email_date

        self.records.clear()
        self.raw_results.clear()

        # Sort emails chronologically
        sorted_emails = sorted(emails, key=lambda x: x.date)

        for email in sorted_emails:
            classification = classify_email(email)
            self.raw_results.append(classification)

            # Application key (unique per company & role)
            app_key = f"{classification.company}::{classification.role}".lower()

            elapsed_days = max(0, (self.reference_date - email.date).days)

            follow_up_due = False
            follow_up_reason = None
            follow_up_template = None

            if classification.stage == StageEnum.APPLIED:
                if elapsed_days >= 7:
                    follow_up_due = True
                    follow_up_reason = f"No response received in {elapsed_days} days (threshold: 7 days). Follow-up recommended!"
                    follow_up_template = generate_follow_up_template(
                        company=classification.company,
                        role=classification.role,
                        days_elapsed=elapsed_days
                    )
                else:
                    days_left = 7 - elapsed_days
                    follow_up_reason = f"Application under review ({elapsed_days}d ago). Wait {days_left} more day(s) before following up."
            elif classification.stage == StageEnum.SCAM:
                follow_up_due = False
                follow_up_reason = "DO NOT ENGAGE: Confirmed fake offer / recruitment scam."

            record = ApplicationRecord(
                id=f"app_{len(self.records) + 1:03d}",
                company=classification.company,
                role=classification.role,
                current_stage=classification.stage,
                application_date=email.date,
                last_update_date=email.date,
                days_elapsed=elapsed_days,
                follow_up_due=follow_up_due,
                follow_up_reason=follow_up_reason,
                follow_up_template=follow_up_template,
                is_scam=(classification.stage == StageEnum.SCAM),
                scam_reasons=classification.scam_analysis.reasons if classification.stage == StageEnum.SCAM else [],
                latest_subject=email.subject,
                sender=email.sender,
                sender_email=email.sender_email,
                raw_body=email.body,
                history=[{
                    "date": email.date.isoformat(),
                    "subject": email.subject,
                    "stage": classification.stage.value,
                    "summary": classification.summary
                }]
            )

            self.records[app_key] = record

        return list(self.records.values())

    def get_stats(self) -> TrackerStats:
        """Calculate high-level dashboard metrics."""
        records = list(self.records.values())
        stage_counts = {
            StageEnum.APPLIED.value: 0,
            StageEnum.INTERVIEW.value: 0,
            StageEnum.REJECTED.value: 0,
            StageEnum.OFFER.value: 0,
            StageEnum.SCAM.value: 0,
        }

        for r in records:
            stage_counts[r.current_stage.value] = stage_counts.get(r.current_stage.value, 0) + 1

        scams_flagged = stage_counts.get(StageEnum.SCAM.value, 0)
        follow_ups_due = sum(1 for r in records if r.follow_up_due)
        offers_received = stage_counts.get(StageEnum.OFFER.value, 0)
        interviews_scheduled = stage_counts.get(StageEnum.INTERVIEW.value, 0)
        rejections_count = stage_counts.get(StageEnum.REJECTED.value, 0)

        return TrackerStats(
            total_emails=len(self.raw_results),
            total_applications=len(records),
            stage_counts=stage_counts,
            scams_flagged=scams_flagged,
            follow_ups_due=follow_ups_due,
            offers_received=offers_received,
            interviews_scheduled=interviews_scheduled,
            rejections_count=rejections_count
        )
