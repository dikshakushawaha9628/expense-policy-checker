"""Ingestion: file -> RAW table -> cleaned CURATED table (+ rejected_records).

Guarantees
* Raw layer keeps every row exactly as read (TEXT), so nothing is lost.
* Re-running on the same file inserts nothing new (row_hash UNIQUE).
* New rows in a later file are appended (incremental load).
* Bad rows are never silently dropped: each gets a rejected_records reason.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_COLUMNS = [
    "expense_id", "employee_id", "expense_date", "submitted_date", "merchant",
    "category", "amount", "currency", "description", "receipt_attached", "approver_id",
]

CATEGORY_ALIASES = {
    "meals": "Meals", "meal": "Meals", "food": "Meals",
    "lodging": "Lodging", "hotel": "Lodging",
    "airfare": "Airfare", "flight": "Airfare", "air": "Airfare",
    "ground transport": "Ground Transport", "taxi": "Ground Transport", "transport": "Ground Transport",
    "office supplies": "Office Supplies", "supplies": "Office Supplies",
    "software": "Software",
    "entertainment": "Entertainment",
    "alcohol": "Alcohol",
    "personal": "Personal",
}
DATE_FORMATS = ("%Y-%m-%d", "%d-%b-%Y", "%m/%d/%Y")
TRUE_VALUES = {"1", "y", "yes", "true", "t"}
FALSE_VALUES = {"0", "n", "no", "false", "f", ""}  # blank == no receipt (documented assumption)


class SchemaError(ValueError):
    """The input file does not have the columns we need."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- pure cleaning helpers (unit-tested) ----------

def parse_date(value: str | None) -> str | None:
    value = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_amount(value: str | None) -> float | None:
    cleaned = re.sub(r"[,\s$£€₹]", "", (value or ""))
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return round(number, 2) if math.isfinite(number) else None


def parse_receipt(value: str | None) -> int | None:
    v = (value or "").strip().lower()
    if v in TRUE_VALUES:
        return 1
    if v in FALSE_VALUES:
        return 0
    return None


def normalise_category(value: str | None) -> str | None:
    return CATEGORY_ALIASES.get((value or "").strip().lower())


def clean_row(raw: dict[str, str], valid_currencies: set[str]) -> tuple[dict | None, list[str]]:
    """Return (clean_record, []) or (None, [reasons...])."""
    reasons: list[str] = []
    get = lambda k: (raw.get(k) or "").strip()  # noqa: E731

    for field in ("expense_id", "employee_id", "merchant"):
        if not get(field):
            reasons.append(f"missing {field}")

    expense_date = parse_date(raw.get("expense_date"))
    submitted_date = parse_date(raw.get("submitted_date"))
    if expense_date is None:
        reasons.append(f"invalid expense_date '{get('expense_date')}'")
    if submitted_date is None:
        reasons.append(f"invalid submitted_date '{get('submitted_date')}'")

    amount = parse_amount(raw.get("amount"))
    if amount is None:
        reasons.append(f"invalid amount '{get('amount')}'")
    elif amount <= 0:
        reasons.append(f"non-positive amount {amount} (refunds out of scope)")

    category = normalise_category(raw.get("category"))
    if category is None:
        reasons.append(f"unknown category '{get('category')}'")

    currency = get("currency").upper()
    if currency not in valid_currencies:
        reasons.append(f"unsupported currency '{get('currency')}'")

    receipt = parse_receipt(raw.get("receipt_attached"))
    if receipt is None:
        reasons.append(f"invalid receipt_attached '{get('receipt_attached')}'")

    if reasons:
        return None, reasons
    return {
        "expense_id": get("expense_id"),
        "employee_id": get("employee_id"),
        "expense_date": expense_date,
        "submitted_date": submitted_date,
        "merchant": get("merchant"),
        "category": category,
        "amount": amount,
        "currency": currency,
        "description": get("description"),
        "receipt_attached": receipt,
        "approver_id": get("approver_id") or None,
    }, []


def row_hash(raw: dict[str, str]) -> str:
    canonical = "\x1f".join((raw.get(c) or "").strip() for c in EXPECTED_COLUMNS)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------- database loading ----------

@dataclass
class IngestStats:
    source_file: str
    rows_read: int = 0
    rows_new: int = 0
    rows_skipped_existing: int = 0
    rows_rejected: int = 0


def ingest_file(conn: sqlite3.Connection, path: str | Path) -> IngestStats:
    path = Path(path)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in EXPECTED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:  # schema problem: fail loudly BEFORE touching the database
            raise SchemaError(f"{path.name}: missing required columns {missing}")
        rows = list(reader)

    valid_currencies = {r["currency"] for r in conn.execute("SELECT currency FROM fx_rates")}
    stats = IngestStats(source_file=path.name)
    now = utc_now()

    with conn:  # one transaction per file: all-or-nothing
        batch_id = conn.execute(
            "INSERT INTO ingest_batches(source_file, loaded_at) VALUES (?, ?)", (path.name, now)
        ).lastrowid
        for raw in rows:
            stats.rows_read += 1
            cur = conn.execute(
                f"INSERT OR IGNORE INTO raw_expenses(batch_id, row_hash, {', '.join(EXPECTED_COLUMNS)}) "
                f"VALUES (?, ?, {', '.join('?' * len(EXPECTED_COLUMNS))})",
                (batch_id, row_hash(raw), *[(raw.get(c) or "").strip() for c in EXPECTED_COLUMNS]),
            )
            if cur.rowcount == 0:  # identical row already loaded
                stats.rows_skipped_existing += 1
                continue
            raw_id = cur.lastrowid

            clean, reasons = clean_row(raw, valid_currencies)
            if clean is None:
                _reject(conn, batch_id, raw_id, raw.get("expense_id"), "; ".join(reasons), now)
                stats.rows_rejected += 1
                continue

            try:
                conn.execute(
                    "INSERT INTO expenses(raw_id, expense_id, employee_id, expense_date, submitted_date, "
                    "merchant, category, amount, currency, description, receipt_attached, approver_id) "
                    "VALUES (:raw_id, :expense_id, :employee_id, :expense_date, :submitted_date, "
                    ":merchant, :category, :amount, :currency, :description, :receipt_attached, :approver_id)",
                    {**clean, "raw_id": raw_id},
                )
                stats.rows_new += 1
            except sqlite3.IntegrityError:
                _reject(conn, batch_id, raw_id, clean["expense_id"],
                        "expense_id already exists with different content", now)
                stats.rows_rejected += 1

        conn.execute(
            "UPDATE ingest_batches SET rows_read=?, rows_new=?, rows_skipped_existing=?, rows_rejected=? "
            "WHERE batch_id=?",
            (stats.rows_read, stats.rows_new, stats.rows_skipped_existing, stats.rows_rejected, batch_id),
        )
    return stats


def _reject(conn, batch_id, raw_id, expense_id, reason, now) -> None:
    conn.execute(
        "INSERT INTO rejected_records(batch_id, raw_id, expense_id, reason, created_at) VALUES (?,?,?,?,?)",
        (batch_id, raw_id, (expense_id or None), reason, now),
    )
