import unittest

from expense_checker.ai.base import PolicyReviewer, ReviewerError, ReviewInput
from expense_checker.ai.heuristic import HeuristicReviewer
from expense_checker.ai.validation import InvalidResponse, parse_observation
from expense_checker.ai_review import run_ai_review
from expense_checker.ingest import ingest_file
from expense_checker.rules import evaluate_all
from datetime import date
from .helpers import make_db, row, write_csv


class Scripted(PolicyReviewer):
    """Test double: returns whatever it is told to (or raises)."""
    def __init__(self, response=None, exc=None, name="scripted"):
        self.response, self.exc, self.name, self.model = response, exc, name, "test"
    def review(self, item):
        if self.exc:
            raise self.exc
        return self.response


GOOD_JSON = '{"label": "consistent", "confidence": 0.9, "rationale": "fine"}'


class TestValidation(unittest.TestCase):
    def test_valid_json_and_markdown_fenced_json(self):
        self.assertEqual(parse_observation(GOOD_JSON).label, "consistent")
        self.assertEqual(parse_observation("```json\n" + GOOD_JSON + "\n```").confidence, 0.9)

    def test_rejects_bad_outputs(self):
        bad = ["", "looks fine!", "[1,2]",
               '{"label": "made_up", "confidence": 0.9, "rationale": "x"}',
               '{"label": "consistent", "confidence": 7, "rationale": "x"}',
               '{"label": "consistent", "confidence": true, "rationale": "x"}',
               '{"label": "consistent", "confidence": 0.5}']
        for b in bad:
            with self.subTest(b=b), self.assertRaises(InvalidResponse):
                parse_observation(b)


class TestAIOrchestration(unittest.TestCase):
    def setUp(self):
        self.conn = make_db()
        ingest_file(self.conn, write_csv([row(amount="120.00", description="stuff")]))  # fails R001
        evaluate_all(self.conn, date(2026, 10, 15))

    def _status(self):
        return self.conn.execute("SELECT status, needs_human_review FROM ai_observations").fetchone()

    def test_edge_unexpected_ai_response_is_flagged_not_crashing(self):
        stats = run_ai_review(self.conn, Scripted("Sure! Looks fine :)"))
        self.assertEqual(stats.invalid_response, 1)
        self.assertEqual(tuple(self._status()), ("invalid_response", 1))

    def test_edge_provider_failure_is_recorded_and_retried(self):
        run_ai_review(self.conn, Scripted(exc=ReviewerError("down")))
        self.assertEqual(self._status()["status"], "error")
        stats = run_ai_review(self.conn, Scripted(GOOD_JSON))            # retried on next run
        self.assertEqual(stats.ok, 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM ai_observations").fetchone()[0], 1)

    def test_low_confidence_needs_human_review(self):
        run_ai_review(self.conn, Scripted('{"label":"vague_description","confidence":0.3,"rationale":"?"}'), 0.6)
        self.assertEqual(tuple(self._status()), ("low_confidence", 1))

    def test_ai_is_incremental(self):
        r = Scripted(GOOD_JSON)
        self.assertEqual(run_ai_review(self.conn, r).reviewed, 1)
        self.assertEqual(run_ai_review(self.conn, r).reviewed, 0)

    def test_ai_never_changes_deterministic_results(self):
        before = self.conn.execute("SELECT * FROM rule_violations").fetchall()
        run_ai_review(self.conn, Scripted('{"label":"consistent","confidence":0.99,"rationale":"all good"}'))
        after = self.conn.execute("SELECT * FROM rule_violations").fetchall()
        self.assertEqual([tuple(r) for r in before], [tuple(r) for r in after])
        status = self.conn.execute("SELECT rule_status, ai_label FROM v_expense_review").fetchone()
        self.assertEqual(tuple(status), ("FAIL", "consistent"))   # AI says fine, rules still FAIL


class TestHeuristic(unittest.TestCase):
    def test_labels(self):
        h = HeuristicReviewer()
        def label(desc, cat="Meals"):
            return parse_observation(h.review(ReviewInput("x", "m", cat, desc, 10, "USD"))).label
        self.assertEqual(label("misc"), "vague_description")
        self.assertEqual(label("Birthday gift"), "possible_personal_expense")
        self.assertEqual(label("Uber ride to airport"), "category_mismatch")
        self.assertEqual(label("Client lunch"), "consistent")


if __name__ == "__main__":
    unittest.main()
