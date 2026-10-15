"""Orchestrates AI review. Writes ONLY to ai_observations, never to rule_violations.

Failure handling (the pipeline never crashes because of the model):
  provider raised          -> status 'error'            + needs_human_review
  output not valid/schema  -> status 'invalid_response' + needs_human_review
  confidence < threshold   -> status 'low_confidence'   + needs_human_review
  otherwise                -> status 'ok'
Incremental: expenses already reviewed (same provider + prompt version) are skipped;
previous 'error' rows are retried.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .ai.base import PolicyReviewer, ReviewerError, ReviewInput
from .ai.validation import InvalidResponse, parse_observation
from .ingest import utc_now


@dataclass
class AIStats:
    reviewed: int = 0
    ok: int = 0
    low_confidence: int = 0
    invalid_response: int = 0
    error: int = 0


def run_ai_review(conn: sqlite3.Connection, reviewer: PolicyReviewer, min_confidence: float = 0.6) -> AIStats:
    pending = conn.execute(
        """SELECT x.expense_id, x.merchant, x.category, x.description, x.amount, x.currency
           FROM v_expenses_usd x
           WHERE NOT EXISTS (
               SELECT 1 FROM ai_observations o
               WHERE o.expense_id = x.expense_id AND o.provider = ? AND o.prompt_version = ?
                 AND o.status <> 'error')
           ORDER BY x.expense_id""",
        (reviewer.name, reviewer.prompt_version),
    ).fetchall()

    stats = AIStats()
    for row in pending:
        item = ReviewInput(row["expense_id"], row["merchant"], row["category"],
                           row["description"], row["amount"], row["currency"])
        label = confidence = rationale = None
        try:
            obs = parse_observation(reviewer.review(item))
            label, confidence, rationale = obs.label, obs.confidence, obs.rationale
            low = confidence < min_confidence
            status = "low_confidence" if low else "ok"
            needs_review = int(low)
        except ReviewerError as exc:
            status, needs_review, rationale = "error", 1, str(exc)[:300]
        except InvalidResponse as exc:
            status, needs_review, rationale = "invalid_response", 1, str(exc)[:300]

        with conn:
            conn.execute(
                """INSERT OR REPLACE INTO ai_observations(expense_id, provider, model, prompt_version, status,
                       label, confidence, rationale, needs_human_review, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (item.expense_id, reviewer.name, reviewer.model, reviewer.prompt_version, status,
                 label, confidence, rationale, needs_review, utc_now()),
            )
        stats.reviewed += 1
        setattr(stats, status, getattr(stats, status) + 1)
    return stats
