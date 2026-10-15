import unittest
from datetime import date

from expense_checker.rules import evaluate_expense
from .helpers import expense

AS_OF = date(2026, 10, 15)


def ids(**over):
    return {v.rule_id for v in evaluate_expense(expense(**over), AS_OF)}


class TestRules(unittest.TestCase):
    def test_clean_expense_passes_everything(self):
        self.assertEqual(ids(), set())

    def test_meal_limit_boundary(self):
        self.assertNotIn("R001", ids(amount_usd=75.00))      # exactly at limit is fine
        self.assertIn("R001", ids(amount_usd=75.01))

    def test_lodging_limit_only_applies_to_lodging(self):
        self.assertIn("R002", ids(category="Lodging", amount_usd=300))
        self.assertNotIn("R002", ids(category="Airfare", amount_usd=300))

    def test_receipt_threshold(self):
        self.assertIn("R003", ids(amount_usd=25.0, receipt_attached=0))
        self.assertNotIn("R003", ids(amount_usd=24.99, receipt_attached=0))

    def test_prohibited_category(self):
        self.assertIn("R004", ids(category="Alcohol"))

    def test_approval_required_over_500(self):
        self.assertIn("R006", ids(category="Airfare", amount_usd=501, approver_id=None))
        self.assertNotIn("R006", ids(category="Airfare", amount_usd=501, approver_id="M1"))

    def test_late_submission_boundary(self):
        self.assertNotIn("R007", ids(expense_date="2026-08-01", submitted_date="2026-09-30"))  # 60 days
        self.assertIn("R007", ids(expense_date="2026-08-01", submitted_date="2026-10-01"))     # 61 days

    def test_future_dated(self):
        self.assertIn("R008", ids(expense_date="2026-10-16"))
        self.assertNotIn("R008", ids(expense_date="2026-10-15"))

    def test_self_approval(self):
        self.assertIn("R009", ids(approver_id="E1"))

    def test_rules_are_deterministic(self):
        e = expense(category="Meals", amount_usd=200, receipt_attached=0)
        self.assertEqual(evaluate_expense(e, AS_OF), evaluate_expense(e, AS_OF))


if __name__ == "__main__":
    unittest.main()
