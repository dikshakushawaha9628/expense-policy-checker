"""DETERMINISTIC policy rules. Pure functions: same input -> same output, no AI, no I/O.

Each rule takes an expense dict (a row of v_expenses_usd) and the processing
date, and returns a message when violated or None when it passes.
R005 (duplicates) needs the whole table, so it is computed in SQL (v_duplicate_claims).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Callable, Mapping, Optional

from . import policy as P
from .ingest import utc_now


@dataclass(frozen=True)
class Violation:
    rule_id: str
    severity: str
    message: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    name: str
    severity: str
    check: Callable[[Mapping, date], Optional[str]]


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def r001_meal_limit(e, as_of):
    if e["category"] == "Meals" and e["amount_usd"] > P.MEAL_LIMIT_USD:
        return f"Meal of USD {e['amount_usd']:.2f} exceeds limit of USD {P.MEAL_LIMIT_USD:.2f}"


def r002_lodging_limit(e, as_of):
    if e["category"] == "Lodging" and e["amount_usd"] > P.LODGING_LIMIT_USD:
        return f"Lodging of USD {e['amount_usd']:.2f} exceeds limit of USD {P.LODGING_LIMIT_USD:.2f}"


def r003_receipt_required(e, as_of):
    if e["amount_usd"] >= P.RECEIPT_THRESHOLD_USD and not e["receipt_attached"]:
        return f"Receipt required for expenses of USD {P.RECEIPT_THRESHOLD_USD:.0f} or more"


def r004_prohibited_category(e, as_of):
    if e["category"] in P.PROHIBITED_CATEGORIES:
        return f"Category '{e['category']}' is not reimbursable"


def r006_approval_required(e, as_of):
    if e["amount_usd"] > P.APPROVAL_THRESHOLD_USD and not e["approver_id"]:
        return f"Approver required for expenses over USD {P.APPROVAL_THRESHOLD_USD:.0f}"


def r007_late_submission(e, as_of):
    lag = _days(e["submitted_date"], e["expense_date"])
    if lag > P.LATE_SUBMISSION_DAYS:
        return f"Submitted {lag} days after expense date (limit {P.LATE_SUBMISSION_DAYS})"


def r008_future_dated(e, as_of):
    if date.fromisoformat(e["expense_date"]) > as_of:
        return f"Expense date {e['expense_date']} is after processing date {as_of.isoformat()}"


def r009_self_approval(e, as_of):
    if e["approver_id"] and e["approver_id"] == e["employee_id"]:
        return "Employee cannot approve their own expense"


RULES: list[Rule] = [
    Rule("R001", "Meal limit", "medium", r001_meal_limit),
    Rule("R002", "Lodging limit", "medium", r002_lodging_limit),
    Rule("R003", "Receipt required", "high", r003_receipt_required),
    Rule("R004", "Prohibited category", "high", r004_prohibited_category),
    Rule("R006", "Approval required", "high", r006_approval_required),
    Rule("R007", "Late submission", "medium", r007_late_submission),
    Rule("R008", "Future-dated expense", "high", r008_future_dated),
    Rule("R009", "Self approval", "high", r009_self_approval),
]


def evaluate_expense(expense: Mapping, as_of: date) -> list[Violation]:
    out = []
    for rule in RULES:
        message = rule.check(expense, as_of)
        if message:
            out.append(Violation(rule.rule_id, rule.severity, message))
    return out


def evaluate_all(conn: sqlite3.Connection, as_of: date) -> int:
    """Recompute every violation from scratch (idempotent). Returns violation count."""
    now = utc_now()
    rows: list[tuple] = []
    for e in conn.execute("SELECT * FROM v_expenses_usd"):
        for v in evaluate_expense(dict(e), as_of):
            rows.append((e["expense_id"], v.rule_id, v.severity, v.message, P.POLICY_VERSION, now))
    for d in conn.execute("SELECT expense_id, first_expense_id FROM v_duplicate_claims"):
        rows.append((d["expense_id"], "R005", "high",
                     f"Duplicate of {d['first_expense_id']} (same employee, date, merchant, amount)",
                     P.POLICY_VERSION, now))
    with conn:
        conn.execute("DELETE FROM rule_violations")
        conn.executemany(
            "INSERT INTO rule_violations(expense_id, rule_id, severity, message, policy_version, evaluated_at) "
            "VALUES (?,?,?,?,?,?)", rows)
    return len(rows)
