"""
Standard library unittest suite for Job Hunt Autopilot.
No external test runner required.
"""

import os
import unittest
from datetime import datetime, timezone

from job_autopilot.models import StageEnum
from job_autopilot.parser import load_inbox, load_from_json, load_from_mbox
from job_autopilot.classifier import classify_email
from job_autopilot.tracker import JobHuntTracker


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
JSON_FILE = os.path.join(DATA_DIR, "sample_inbox.json")
MBOX_FILE = os.path.join(DATA_DIR, "sample_inbox.mbox")


class TestJobHuntAutopilot(unittest.TestCase):

    def test_json_loading(self):
        """Verify JSON loader parses all 20 messages with valid fields."""
        messages = load_from_json(JSON_FILE)
        self.assertEqual(len(messages), 20)
        for msg in messages:
            self.assertTrue(msg.id)
            self.assertTrue(msg.subject)
            self.assertTrue(msg.body)
            self.assertIsNotNone(msg.date.tzinfo)

    def test_mbox_loading(self):
        """Verify mbox loader parses all 20 messages with valid fields."""
        messages = load_from_mbox(MBOX_FILE)
        self.assertEqual(len(messages), 20)
        for msg in messages:
            self.assertTrue(msg.id)
            self.assertTrue(msg.subject)
            self.assertTrue(msg.body)
            self.assertIsNotNone(msg.date.tzinfo)

    def test_unified_pipeline_classification(self):
        """Verify each email is classified accurately into one of the 5 stages."""
        messages = load_inbox(JSON_FILE)
        tracker = JobHuntTracker(reference_date=datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc))
        records = tracker.process_emails(messages)
        stats = tracker.get_stats()

        self.assertEqual(stats.total_emails, 20)
        self.assertEqual(stats.offers_received, 2)
        self.assertEqual(stats.interviews_scheduled, 4)
        self.assertEqual(stats.rejections_count, 4)
        self.assertEqual(stats.scams_flagged, 5)
        self.assertEqual(stats.stage_counts[StageEnum.APPLIED.value], 5)

    def test_scam_detection_accuracy(self):
        """Verify all 5 scam archetypes are caught with detailed reasons."""
        messages = load_inbox(JSON_FILE)
        scam_msgs = [m for m in messages if m.id in ["msg_016", "msg_017", "msg_018", "msg_019", "msg_020"]]
        self.assertEqual(len(scam_msgs), 5)

        for msg in scam_msgs:
            res = classify_email(msg)
            self.assertEqual(res.stage, StageEnum.SCAM)
            self.assertTrue(res.scam_analysis.is_scam)
            self.assertGreaterEqual(len(res.scam_analysis.reasons), 1)
            self.assertGreaterEqual(res.scam_analysis.risk_score, 0.50)

    def test_legitimate_offers_not_flagged(self):
        """Verify legitimate offers from Linear and Vercel are never flagged as scam."""
        messages = load_inbox(JSON_FILE)
        offer_msgs = [m for m in messages if m.id in ["msg_014", "msg_015"]]
        self.assertEqual(len(offer_msgs), 2)

        for msg in offer_msgs:
            res = classify_email(msg)
            self.assertEqual(res.stage, StageEnum.OFFER)
            self.assertFalse(res.scam_analysis.is_scam)

    def test_follow_up_logic_seven_days(self):
        """Verify 7-day threshold calculates follow-up due dates and generates templates."""
        messages = load_inbox(JSON_FILE)
        ref_date = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)
        tracker = JobHuntTracker(reference_date=ref_date)
        records = tracker.process_emails(messages)

        overdue_companies = {r.company for r in records if r.follow_up_due}
        self.assertIn("Notion", overdue_companies)
        self.assertIn("Airbnb", overdue_companies)
        self.assertIn("Datadog", overdue_companies)
        self.assertNotIn("Stripe", overdue_companies)
        self.assertNotIn("Figma", overdue_companies)

        for r in records:
            if r.follow_up_due:
                self.assertIsNotNone(r.follow_up_template)
                self.assertIn(r.company, r.follow_up_template)
                self.assertIn("Alex Chen", r.follow_up_template)
                self.assertIn(f"{r.days_elapsed} days ago", r.follow_up_template)


if __name__ == "__main__":
    unittest.main()
