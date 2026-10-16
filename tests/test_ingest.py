import unittest

from expense_checker.ingest import (SchemaError, clean_row, ingest_file, parse_amount,
                                    parse_date, normalise_category)
from .helpers import make_db, row, write_csv


class TestCleaningHelpers(unittest.TestCase):
    def test_parse_amount_handles_symbols_and_garbage(self):
        self.assertEqual(parse_amount("$1,020.50"), 1020.50)
        for bad in ("", "N/A", "nan", "inf", None):
            self.assertIsNone(parse_amount(bad))

    def test_parse_date_multiple_formats_and_invalid(self):
        self.assertEqual(parse_date("29-Sep-2026"), "2026-09-29")
        self.assertEqual(parse_date("2026-09-29"), "2026-09-29")
        self.assertIsNone(parse_date("13/45/2026"))

    def test_category_aliases(self):
        self.assertEqual(normalise_category(" Meal "), "Meals")
        self.assertIsNone(normalise_category("Snacks"))

    def test_clean_row_collects_every_reason(self):
        clean, reasons = clean_row(row(amount="", currency="XYZ", employee_id=""), {"USD"})
        self.assertIsNone(clean)
        self.assertEqual(len(reasons), 3)


class TestIngest(unittest.TestCase):
    def test_edge_invalid_rows_are_rejected_not_dropped(self):
        conn = make_db()
        path = write_csv([row(), row(expense_id="T2", amount="abc"), row(expense_id="T3", amount="-5")])
        s = ingest_file(conn, path)
        self.assertEqual((s.rows_read, s.rows_new, s.rows_rejected), (3, 1, 2))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM rejected_records").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_expenses").fetchone()[0], 3)  # raw keeps all

    def test_reingest_same_file_is_idempotent(self):
        conn = make_db()
        path = write_csv([row(), row(expense_id="T2")])
        ingest_file(conn, path)
        s2 = ingest_file(conn, path)
        self.assertEqual((s2.rows_new, s2.rows_skipped_existing), (0, 2))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], 2)

    def test_raw_layer_preserves_source_values(self):
        conn = make_db()
        path = write_csv([row(merchant=" Cafe ", description="  Client lunch  ", amount=" $20.00 ")])
        ingest_file(conn, path)
        raw = conn.execute("SELECT merchant, description, amount FROM raw_expenses").fetchone()
        curated = conn.execute("SELECT merchant, description, amount FROM expenses").fetchone()
        self.assertEqual(tuple(raw), (" Cafe ", "  Client lunch  ", " $20.00 "))
        self.assertEqual(tuple(curated), ("Cafe", "Client lunch", 20.0))

    def test_incremental_load_appends_only_new_rows(self):
        conn = make_db()
        ingest_file(conn, write_csv([row()], "a.csv"))
        s = ingest_file(conn, write_csv([row(), row(expense_id="T2")], "b.csv"))
        self.assertEqual((s.rows_new, s.rows_skipped_existing), (1, 1))

    def test_conflicting_expense_id_is_rejected(self):
        conn = make_db()
        ingest_file(conn, write_csv([row()], "a.csv"))
        s = ingest_file(conn, write_csv([row(amount="99.00")], "b.csv"))  # same id, different content
        self.assertEqual(s.rows_rejected, 1)
        reason = conn.execute("SELECT reason FROM rejected_records").fetchone()[0]
        self.assertIn("already exists", reason)

    def test_edge_schema_problem_fails_before_writing(self):
        import tempfile, pathlib
        conn = make_db()
        p = pathlib.Path(tempfile.mkdtemp()) / "bad.csv"
        p.write_text("expense_id,amount\nX,1\n")
        with self.assertRaises(SchemaError):
            ingest_file(conn, p)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM ingest_batches").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
