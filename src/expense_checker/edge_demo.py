"""`expense-checker edge-demo`: shows the failure paths on a throw-away in-memory DB."""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from .ai.base import PolicyReviewer, ReviewerError, ReviewInput
from .ai_review import run_ai_review
from .db import connect, init_db
from .ingest import ingest_file, SchemaError
from .report import build_report
from .rules import evaluate_all

HEADER = "expense_id,employee_id,expense_date,submitted_date,merchant,category,amount,currency,description,receipt_attached,approver_id\n"
GOOD = HEADER + (
    "X1,E1,2026-10-01,2026-10-02,Cafe,Meals,120.00,USD,Client lunch,yes,\n"          # R001 fail
    "X2,E1,2026-10-01,2026-10-02,Cafe,Meals,20.00,USD,Client lunch,yes,\n"           # clean
    "X3,E2,2026-10-01,2026-10-02,Cafe,Meals,abc,USD,Lunch,yes,\n"                    # bad amount -> rejected
)


class GarbageModel(PolicyReviewer):
    name, model = "garbage", "broken-llm"
    def review(self, item: ReviewInput) -> str:
        return "Sure! I think this looks fine :)"          # not JSON


class OfflineModel(PolicyReviewer):
    name, model = "offline", "unreachable"
    def review(self, item: ReviewInput) -> str:
        raise ReviewerError("connection refused (model server is down)")


def main() -> None:
    conn = connect(":memory:")
    init_db(conn)
    tmp = Path(tempfile.mkdtemp())

    print("\n### EDGE CASE 1: schema problem - file is missing columns")
    bad = tmp / "bad_schema.csv"
    bad.write_text("expense_id,amount\nX1,10\n")
    try:
        ingest_file(conn, bad)
    except SchemaError as exc:
        print(f"  -> SchemaError raised before any DB write: {exc}")
    print(f"  -> expenses in DB: {conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]}")

    print("\n### EDGE CASE 2: invalid value inside an otherwise good file")
    good = tmp / "good.csv"
    good.write_text(GOOD)
    s = ingest_file(conn, good)
    print(f"  -> read={s.rows_read} new={s.rows_new} rejected={s.rows_rejected}")
    for r in conn.execute("SELECT expense_id, reason FROM rejected_records"):
        print(f"     rejected {r['expense_id']}: {r['reason']}")

    print("\n### EDGE CASE 3: run it again - idempotency")
    s = ingest_file(conn, good)
    print(f"  -> read={s.rows_read} new={s.rows_new} skipped_existing={s.rows_skipped_existing}")

    evaluate_all(conn, date(2026, 10, 15))

    print("\n### EDGE CASE 4: AI returns garbage / AI is down")
    for model in (GarbageModel(), OfflineModel()):
        st = run_ai_review(conn, model)
        print(f"  -> {model.name}: invalid_response={st.invalid_response} error={st.error}")
    print("\n  Deterministic result is untouched by AI failure:")
    for r in conn.execute("SELECT expense_id, rule_status, failed_rules FROM v_expense_review ORDER BY expense_id"):
        print(f"     {r['expense_id']}: {r['rule_status']} {r['failed_rules']}")
    print("\n  AI rows are flagged for humans, not guessed:")
    for r in conn.execute("SELECT provider, status, needs_human_review, rationale FROM ai_observations"):
        print(f"     {r['provider']:8} {r['status']:17} human_review={r['needs_human_review']}  ({r['rationale'][:45]})")


if __name__ == "__main__":
    main()
