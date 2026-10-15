"""Local-model provider via Ollama's HTTP API (https://ollama.com). Free, runs on
your machine, no API key. Uses only urllib (no extra dependency).

    ollama pull llama3.2
    AI_PROVIDER=ollama python -m expense_checker ai
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import ALLOWED_LABELS, PolicyReviewer, ReviewerError, ReviewInput

PROMPT_TEMPLATE = """You are an expense auditor assistant. You give ADVISORY observations only;
hard policy rules (limits, receipts, duplicates) are checked elsewhere - do NOT judge them.

Decide whether the description is consistent with the category and looks like a business expense.
Answer with ONE JSON object and nothing else:
{{"label": one of {labels}, "confidence": number between 0 and 1, "rationale": "<one sentence>"}}

Expense:
- merchant: {merchant}
- category: {category}
- description: {description}
- amount: {amount} {currency}
"""


class OllamaReviewer(PolicyReviewer):
    name = "ollama"

    def __init__(self, url: str, model: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def review(self, item: ReviewInput) -> str:
        prompt = PROMPT_TEMPLATE.format(labels=list(ALLOWED_LABELS), merchant=item.merchant,
                                        category=item.category, description=item.description,
                                        amount=item.amount, currency=item.currency)
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False,
                           "format": "json", "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(f"{self.url}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())["response"]
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError) as exc:
            raise ReviewerError(f"ollama request failed: {exc}") from exc
