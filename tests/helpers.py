import csv
import tempfile
from pathlib import Path

from expense_checker.db import connect, init_db
from expense_checker.ingest import EXPECTED_COLUMNS


def make_db():
    conn = connect(":memory:")
    init_db(conn)
    return conn


def write_csv(rows: list[dict], name: str = "t.csv") -> Path:
    path = Path(tempfile.mkdtemp()) / name
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EXPECTED_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def row(**over) -> dict:
    base = {"expense_id": "T1", "employee_id": "E1", "expense_date": "2026-10-01",
            "submitted_date": "2026-10-03", "merchant": "Cafe", "category": "Meals",
            "amount": "20.00", "currency": "USD", "description": "Client lunch",
            "receipt_attached": "yes", "approver_id": ""}
    base.update(over)
    return base


def expense(**over) -> dict:
    """An already-cleaned expense dict (as served by v_expenses_usd)."""
    base = {"expense_id": "T1", "employee_id": "E1", "expense_date": "2026-10-01",
            "submitted_date": "2026-10-03", "merchant": "Cafe", "category": "Meals",
            "amount": 20.0, "amount_usd": 20.0, "currency": "USD", "description": "Client lunch",
            "receipt_attached": 1, "approver_id": None}
    base.update(over)
    return base
