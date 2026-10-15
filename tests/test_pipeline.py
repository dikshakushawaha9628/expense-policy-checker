import unittest
from datetime import date
from pathlib import Path

from expense_checker.config import SAMPLE_DIR
from expense_checker.ai.heuristic import HeuristicReviewer
from expense_checker.ingest import ingest_file
from expense_checker.pipeline import run_pipeline
from expense_checker.rules import evaluate_all
from .helpers import make_db, row, write_csv

AS_OF = date(2026, 10, 15)


class TestSQLRules(unittest.TestCase):
    def test_duplicate_claim_flags_later_copy_only(self):
        conn = make_db()
        ingest_file(conn, write_csv([row(expense_id="A"), row(expense_id="B"), row(expense_id="C", amount="21.00")]))
        evaluate_all(conn, AS_OF)
        dups = conn.execute("SELECT expense_id FROM rule_violations WHERE rule_id='R005'").fetchall()
        self.assertEqual([d[0] for d in dups], ["B"])

    def test_fx_conversion_drives_limits(self):
        conn = make_db()
        # 9000 INR = 108 USD > 75 meal limit; 3500 INR = 42 USD is fine
        ingest_file(conn, write_csv([row(expense_id="A", amount="9000", currency="INR"),
                                     row(expense_id="B", amount="3500", currency="INR")]))
        evaluate_all(conn, AS_OF)
        failed = {r[0] for r in conn.execute("SELECT expense_id FROM rule_violations WHERE rule_id='R001'")}
        self.assertEqual(failed, {"A"})

    def test_rule_evaluation_is_idempotent(self):
        conn = make_db()
        ingest_file(conn, write_csv([row(amount="500", category="Meals")]))
        evaluate_all(conn, AS_OF)
        evaluate_all(conn, AS_OF)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM rule_violations").fetchone()[0], 1)


class TestEndToEndSample(unittest.TestCase):
    """Runs the shipped sample data; numbers are pinned so regressions are obvious."""

    @classmethod
    def setUpClass(cls):
        cls.conn = make_db()
        files = [SAMPLE_DIR / "expenses_batch1.csv", SAMPLE_DIR / "expenses_batch2.csv"]
        cls.stats, cls.violations, cls.ai = run_pipeline(cls.conn, files, AS_OF, HeuristicReviewer())

    def test_load_counts(self):
        self.assertEqual([s.rows_new for s in self.stats], [112, 4])
        self.assertEqual([s.rows_rejected for s in self.stats], [7, 0])
        self.assertEqual(self.stats[1].rows_skipped_existing, 8)

    def test_each_rule_fires_on_the_sample(self):
        fired = {r[0] for r in self.conn.execute("SELECT DISTINCT rule_id FROM rule_violations")}
        self.assertEqual(fired, {"R001", "R002", "R003", "R004", "R005", "R006", "R007", "R008", "R009"})

    def test_ai_findings_are_separate_from_rule_failures(self):
        rows = self.conn.execute(
            "SELECT * FROM v_expense_review WHERE rule_status='PASS' AND ai_label IN "
            "('vague_description','possible_personal_expense','category_mismatch')").fetchall()
        self.assertGreaterEqual(len(rows), 5)           # AI flagged items the rules passed
        self.assertTrue(all(r["failed_rules"] == "" for r in rows))

    def test_second_full_run_changes_nothing(self):
        before = self.conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        files = [SAMPLE_DIR / "expenses_batch1.csv", SAMPLE_DIR / "expenses_batch2.csv"]
        stats, n, ai = run_pipeline(self.conn, files, AS_OF, HeuristicReviewer())
        self.assertEqual(sum(s.rows_new for s in stats), 0)
        self.assertEqual(ai.reviewed, 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], before)


if __name__ == "__main__":
    unittest.main()
