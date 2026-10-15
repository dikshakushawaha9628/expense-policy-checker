"""Synthetic data generator (seeded => reproducible). No real people or companies.

Writes two files so incremental loading can be demonstrated:
  expenses_batch1.csv  ~100 mostly-clean rows + injected policy/AI/dirty-data cases
  expenses_batch2.csv  re-sent rows from batch 1 (should be skipped) + a few new ones
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from .ingest import EXPECTED_COLUMNS, parse_date

ANCHOR = date(2026, 10, 15)  # "today" for the sample data; pass --as-of 2026-10-15 when checking

MERCHANTS = {
    "Meals": [("Blue Fork Bistro", "Lunch with client"), ("Corner Cafe", "Working lunch"),
              ("Noodle House", "Team dinner during travel"), ("Sunrise Diner", "Breakfast on business trip")],
    "Lodging": [("Harbor Hotel", "Hotel stay for conference"), ("City Inn", "Overnight stay, client site")],
    "Airfare": [("SkyJet Airlines", "Flight to client workshop"), ("AeroBlue", "Return flight, quarterly review")],
    "Ground Transport": [("QuickCab", "Taxi to client office"), ("RideNow", "Airport transfer")],
    "Office Supplies": [("PaperPlus", "Printer paper and toner"), ("DeskDepot", "Notebooks for workshop")],
    "Software": [("CodeTools Inc", "IDE licence renewal"), ("CloudNotes", "Team notes subscription")],
    "Entertainment": [("Skyline Events", "Client appreciation event")],
}
AMOUNT_RANGE = {  # USD, kept inside policy limits for the "clean" population
    "Meals": (12, 70), "Lodging": (90, 240), "Airfare": (180, 480),
    "Ground Transport": (8, 60), "Office Supplies": (6, 120),
    "Software": (9, 300), "Entertainment": (40, 200),
}


def _fmt(d: date) -> str:
    return d.isoformat()


def _row(employee, exp_date, merchant, category, amount, currency="USD", desc="", receipt="yes",
         approver="", submitted=None):
    submitted = submitted or exp_date + timedelta(days=3)
    return {
        "expense_id": "", "employee_id": employee, "expense_date": _fmt(exp_date),
        "submitted_date": _fmt(submitted), "merchant": merchant, "category": category,
        "amount": f"{amount:.2f}" if isinstance(amount, (int, float)) else amount,
        "currency": currency, "description": desc, "receipt_attached": receipt, "approver_id": approver,
    }


def build_rows(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    employees = [f"E{n:03d}" for n in range(1, 21)]
    rows: list[dict] = []

    # --- clean population -------------------------------------------------
    for _ in range(90):
        cat = rng.choices(list(MERCHANTS), weights=[30, 8, 10, 20, 10, 8, 6])[0]
        merchant, desc = rng.choice(MERCHANTS[cat])
        lo, hi = AMOUNT_RANGE[cat]
        amount = round(rng.uniform(lo, hi), 2)
        emp = rng.choice(employees)
        d = ANCHOR - timedelta(days=rng.randint(5, 80))
        approver = "M001" if amount > 500 else ""
        rows.append(_row(emp, d, merchant, cat, amount, desc=desc,
                         receipt="yes" if amount >= 25 else rng.choice(["yes", "no"]),
                         approver=approver))

    d = lambda n: ANCHOR - timedelta(days=n)  # noqa: E731

    # --- deterministic rule violations -----------------------------------
    rows += [
        _row("E003", d(20), "Blue Fork Bistro", "Meals", 112.40, desc="Dinner with client"),                 # R001
        _row("E004", d(25), "Harbor Hotel", "Lodging", 310.00, desc="Hotel stay for conference"),            # R002
        _row("E005", d(18), "Corner Cafe", "Meals", 64.00, desc="Working lunch", receipt="no"),              # R003
        _row("E006", d(15), "Night Owl Bar", "Alcohol", 48.50, desc="Drinks after work"),                    # R004
        _row("E007", d(30), "CodeTools Inc", "Software", 750.00, desc="Annual licence, 5 seats"),            # R006
        _row("E008", d(12), "SkyJet Airlines", "Airfare", 640.00, desc="Flight to HQ", approver="E008"),     # R009
        _row("E009", d(150), "PaperPlus", "Office Supplies", 55.00, desc="Stationery order",
             submitted=d(40)),                                                                               # R007
        _row("E010", d(-35), "Skyline Events", "Entertainment", 90.00, desc="Client event",
             submitted=d(1)),                                                                                # R008
        _row("E011", d(22), "Berlin Stay", "Lodging", 280.00, "EUR", "Hotel in Berlin"),                     # R002 via FX (302 USD)
        _row("E012", d(10), "Mumbai Bites", "Meals", 9000, "INR", "Client dinner, Mumbai"),                  # R001 via FX (108 USD)
        _row("E013", d(11), "Mumbai Bites", "Meals", 3500, "INR", "Lunch, Mumbai office visit"),             # passes (42 USD)
    ]
    dup = _row("E014", d(14), "QuickCab", "Ground Transport", 34.20, desc="Taxi to client office")
    rows += [dup, dict(dup)]                                                                                 # R005 pair

    # --- rules pass, but a human would raise an eyebrow -> AI observations
    rows += [
        _row("E015", d(9), "GiftBox", "Office Supplies", 40.00, desc="Birthday gift for colleague"),
        _row("E016", d(8), "Corner Cafe", "Meals", 30.00, desc="misc"),
        _row("E017", d(7), "StreamFlix", "Software", 15.49, desc="Netflix subscription", receipt="no"),
        _row("E018", d(6), "RideNow", "Meals", 41.00, desc="Uber ride to airport"),
        _row("E019", d(5), "Zen Spa", "Entertainment", 120.00, desc="Spa day"),
        _row("E020", d(4), "Skyline Events", "Entertainment", 85.00, desc="Evening out"),
        _row("E001", d(3), "Harbor Hotel", "Meals", 55.00, desc="Hotel booking for weekend"),
    ]

    # --- dirty data: cleaned OK (messy but recoverable) -------------------
    rows += [
        _row("E002", d(16), "Corner Cafe", "meal", "$42.50", desc="Lunch with client"),
        _row("E003", d(17), "City Inn", "hotel", "1,020.00", "usd", "Conference hotel, 4 nights",
             approver="M002"),
    ]
    rows[-2]["expense_date"] = (d(16)).strftime("%d-%b-%Y")

    # --- dirty data: must be REJECTED -------------------------------------
    rows += [
        _row("E004", d(13), "Corner Cafe", "Meals", "", desc="Lunch"),                 # blank amount
        _row("E005", d(13), "Corner Cafe", "Meals", "N/A", desc="Lunch"),              # non-numeric
        _row("E006", d(13), "SkyJet Airlines", "Airfare", -220.00, desc="Refund"),     # negative
        _row("E007", d(13), "Corner Cafe", "Meals", 22.00, "XYZ", "Lunch"),            # bad currency
        _row("", d(13), "Corner Cafe", "Meals", 22.00, desc="Lunch"),                  # missing employee
        _row("E008", d(13), "Corner Cafe", "Snacks", 9.00, desc="Vending"),            # unknown category
        _row("E009", d(13), "Corner Cafe", "Meals", 22.00, desc="Lunch"),              # impossible date (set below)
    ]
    rows[-1]["expense_date"] = "13/45/2026"
    return rows


def write_samples(out_dir: Path, seed: int = 42) -> list[Path]:
    rows = build_rows(seed)
    rows.sort(key=lambda r: parse_date(r["expense_date"]) or "9999-99-99")  # unparseable dates last
    for i, r in enumerate(rows, start=1):
        r["expense_id"] = f"EXP-{i:04d}"

    out_dir.mkdir(parents=True, exist_ok=True)
    batch1 = out_dir / "expenses_batch1.csv"
    _write(batch1, rows)

    rng = random.Random(seed + 1)
    resent = rng.sample(rows[:60], 8)  # exact re-sends => must be skipped on ingest
    start = len(rows) + 1
    new = [
        _row("E002", ANCHOR - timedelta(days=2), "Sunrise Diner", "Meals", 18.75, desc="Breakfast on business trip"),
        _row("E009", ANCHOR - timedelta(days=2), "AeroBlue", "Airfare", 455.00, desc="Return flight, quarterly review"),
        _row("E012", ANCHOR - timedelta(days=1), "Night Owl Bar", "Meals", 95.00, desc="Dinner and wine"),   # R001
        _row("E015", ANCHOR - timedelta(days=1), "Cloud9 Lounge", "Entertainment", 60.00, desc="Stuff"),
    ]
    for i, r in enumerate(new, start=start):
        r["expense_id"] = f"EXP-{i:04d}"
    batch2 = out_dir / "expenses_batch2.csv"
    _write(batch2, resent + new)
    return [batch1, batch2]


def _write(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=EXPECTED_COLUMNS)
        w.writeheader()
        w.writerows(rows)
