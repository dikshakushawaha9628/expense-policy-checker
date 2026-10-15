"""SQLite helpers: connection, schema/view creation, reference data load."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .config import REFERENCE_DIR, SQL_DIR


def connect(path: str = ":memory:") -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables, views and load FX reference data. Safe to call repeatedly."""
    conn.executescript((SQL_DIR / "schema.sql").read_text())
    load_fx_rates(conn)
    conn.executescript((SQL_DIR / "views.sql").read_text())
    conn.commit()


def load_fx_rates(conn: sqlite3.Connection, path: Path = REFERENCE_DIR / "fx_rates.csv") -> None:
    with open(path, newline="") as fh:
        rows = [(r["currency"].strip().upper(), float(r["rate_to_usd"])) for r in csv.DictReader(fh)]
    conn.executemany("INSERT OR REPLACE INTO fx_rates(currency, rate_to_usd) VALUES (?, ?)", rows)
