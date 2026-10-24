"""
Comprehensive unit test suite for Job Hunt Autopilot.
"""

import os
from datetime import datetime, timezone
import pytest

from job_autopilot.models import StageEnum
from job_autopilot.parser import load_inbox, load_from_json, load_from_mbox
from job_autopilot.classifier import classify_email, analyze_scam_signals
from job_autopilot.tracker import JobHuntTracker


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
JSON_FILE = os.path.join(DATA_DIR, "sample_inbox.json")
MBOX_FILE = os.path.join(DATA_DIR, "sample_inbox.mbox")


def test_json_loading():
    """Verify JSON loader parses all 20 messages with valid fields."""
    messages = load_from_json(JSON_FILE)
    assert len(messages) == 20
    for msg in messages:
        assert msg.id
        assert msg.subject
        assert msg.body
        assert msg.date.tzinfo is not None


def test_mbox_loading():
    """Verify mbox loader parses all 20 messages with valid fields."""
    messages = load_from_mbox(MBOX_FILE)
    assert len(messages) == 20
    for msg in messages:
        assert msg.id
        assert msg.subject
        assert msg.body
        assert msg.date.tzinfo is not None


def test_unified_pipeline_classification():
    """Verify each email is classified accurately into one of the 5 stages."""
    messages = load_inbox(JSON_FILE)
    tracker = JobHuntTracker(reference_date=datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc))
    records = tracker.process_emails(messages)
    stats = tracker.get_stats()

    assert stats.total_emails == 20
    assert stats.offers_received == 2
    assert stats.interviews_scheduled == 4
    assert stats.rejections_count == 4
    assert stats.scams_flagged == 5
    assert stats.stage_counts[StageEnum.APPLIED.value] == 5


def test_scam_detection_accuracy():
    """Verify all 5 scam archetypes are caught with detailed reasons."""
    messages = load_inbox(JSON_FILE)
    scam_msgs = [m for m in messages if m.id in ["msg_016", "msg_017", "msg_018", "msg_019", "msg_020"]]
    assert len(scam_msgs) == 5

    for msg in scam_msgs:
        res = classify_email(msg)
        assert res.stage == StageEnum.SCAM
        assert res.scam_analysis.is_scam is True
        assert len(res.scam_analysis.reasons) >= 1
        assert res.scam_analysis.risk_score >= 0.50


def test_legitimate_offers_not_flagged():
    """Verify legitimate offers from Linear and Vercel are never flagged as scam."""
    messages = load_inbox(JSON_FILE)
    offer_msgs = [m for m in messages if m.id in ["msg_014", "msg_015"]]
    assert len(offer_msgs) == 2

    for msg in offer_msgs:
        res = classify_email(msg)
        assert res.stage == StageEnum.OFFER
        assert res.scam_analysis.is_scam is False


def test_follow_up_logic_seven_days():
    """Verify 7-day threshold calculates follow-up due dates and generates templates."""
    messages = load_inbox(JSON_FILE)
    # Using Oct 24, 2026 as reference date
    ref_date = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)
    tracker = JobHuntTracker(reference_date=ref_date)
    records = tracker.process_emails(messages)
    stats = tracker.get_stats()

    # Notion (Oct 12 -> 12 days), Airbnb (Oct 15 -> 9 days), Datadog (Oct 16 -> 8 days) should be overdue
    # Stripe (Oct 21 -> 3 days), Figma (Oct 22 -> 2 days) should NOT be overdue
    overdue_companies = {r.company for r in records if r.follow_up_due}
    assert "Notion" in overdue_companies
    assert "Airbnb" in overdue_companies
    assert "Datadog" in overdue_companies
    assert "Stripe" not in overdue_companies
    assert "Figma" not in overdue_companies

    # Check template generation
    for r in records:
        if r.follow_up_due:
            assert r.follow_up_template is not None
            assert r.company in r.follow_up_template
            assert "Alex Chen" in r.follow_up_template
            assert f"{r.days_elapsed} days ago" in r.follow_up_template
