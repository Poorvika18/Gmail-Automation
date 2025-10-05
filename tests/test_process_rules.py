import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json
from core.process_rules import RuleProcessor
from core.model import Email


class TestRuleProcessor(unittest.TestCase):

    def setUp(self):
        self.rp = RuleProcessor()
        self.email = Email(
            sender="Poorvi@example.com",
            subject="HappyFox Assignment",
            snippet="Please find the assignment details",
            internal_date=datetime.now() - timedelta(days=3),
            message_id="abc123",
            is_read=False
        )

    def test_get_field_value(self):
        self.assertEqual(self.rp.get_field_value(self.email, "from"), "Poorvi@example.com")
        self.assertEqual(self.rp.get_field_value(self.email, "subject"), "HappyFox Assignment")
        self.assertEqual(self.rp.get_field_value(self.email, "snippet"), "Please find the assignment details")
        self.assertEqual(self.rp.get_field_value(self.email, "nonexistent"), "")


    def test_evaluate_condition_contains(self):
        cond = {"field": "subject", "predicate": "contains", "value": "happyfox"}
        self.assertTrue(self.rp.evaluate_condition(self.email, cond))

    def test_evaluate_condition_does_not_contain(self):
        cond = {"field": "from", "predicate": "does not contain", "value": "other.com"}
        self.assertTrue(self.rp.evaluate_condition(self.email, cond))

    def test_evaluate_condition_equals(self):
        cond = {"field": "from", "predicate": "equals", "value": "Poorvi@example.com"}
        self.assertTrue(self.rp.evaluate_condition(self.email, cond))

    def test_evaluate_condition_date_less_than_days(self):
        cond = {"field": "internal_date", "predicate": "less_than_days", "value": 5}
        self.assertTrue(self.rp.evaluate_condition(self.email, cond))

    def test_evaluate_condition_date_greater_than_days(self):
        cond = {"field": "internal_date", "predicate": "greater_than_days", "value": 4}
        self.assertFalse(self.rp.evaluate_condition(self.email, cond))

if __name__ == "__main__":
    unittest.main()
