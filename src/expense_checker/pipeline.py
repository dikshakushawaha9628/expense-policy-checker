"""End-to-end flow: ingest -> deterministic rules -> (optional) AI review."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from .ai.base import PolicyReviewer
from .ai_review import AIStats, run_ai_review
from .ingest import IngestStats, ingest_file
from .rules import evaluate_all


def run_pipeline(conn: sqlite3.Connection, files: list[Path], as_of: date,
                 reviewer: PolicyReviewer | None, min_confidence: float = 0.6
                 ) -> tuple[list[IngestStats], int, AIStats | None]:
    stats = [ingest_file(conn, f) for f in files]
    violations = evaluate_all(conn, as_of)
    ai = run_ai_review(conn, reviewer, min_confidence) if reviewer else None
    return stats, violations, ai
