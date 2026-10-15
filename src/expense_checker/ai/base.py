"""The ONLY contract between the pipeline and any model.

A provider receives a minimal ReviewInput (no employee/approver IDs -> less PII
leaves the system) and returns raw text that is *supposed* to be JSON. The
pipeline never trusts that text: see validation.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

PROMPT_VERSION = "v1"

ALLOWED_LABELS = (
    "consistent",
    "vague_description",
    "possible_personal_expense",
    "category_mismatch",
    "no_business_purpose",
)


@dataclass(frozen=True)
class ReviewInput:
    expense_id: str
    merchant: str
    category: str
    description: str
    amount: float
    currency: str


class ReviewerError(Exception):
    """Provider could not produce a response (network down, timeout, model missing...)."""


class PolicyReviewer(ABC):
    name: str = "base"
    model: str = "n/a"
    prompt_version: str = PROMPT_VERSION

    @abstractmethod
    def review(self, item: ReviewInput) -> str:
        """Return raw model output (expected: a JSON object). May raise ReviewerError."""
