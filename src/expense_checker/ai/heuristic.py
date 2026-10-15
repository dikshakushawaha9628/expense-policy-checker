"""Offline stand-in 'model' so the project runs from a clean checkout with no
downloads, keys or network. It is deliberately simple keyword logic that emits
the same JSON a real LLM would, so the SAME validation / storage path is used.
Swap it for Ollama by setting AI_PROVIDER=ollama."""
from __future__ import annotations

import json

from .base import PolicyReviewer, ReviewInput

PERSONAL = ("gift", "birthday", "spa", "netflix", "spotify", "gym", "groceries", "wedding", "vacation", "personal")
VAGUE = {"misc", "stuff", "other", "various", "expense", "n/a", "na", "things", "-"}
KEYWORD_CATEGORY = {
    "hotel": "Lodging", "flight": "Airfare", "airline": "Airfare",
    "taxi": "Ground Transport", "uber": "Ground Transport", "ride": "Ground Transport",
    "lunch": "Meals", "dinner": "Meals", "breakfast": "Meals",
    "licence": "Software", "license": "Software", "subscription": "Software",
}
BUSINESS_WORDS = ("client", "conference", "workshop", "team", "customer", "business")


class HeuristicReviewer(PolicyReviewer):
    name = "heuristic"
    model = "keyword-rules-v1"

    def review(self, item: ReviewInput) -> str:
        d = item.description.lower().strip()

        if d in VAGUE or len(d) < 5:
            return self._out("vague_description", 0.92, f"Description '{item.description}' is too vague to audit.")

        hit = next((w for w in PERSONAL if w in d), None)
        if hit:
            return self._out("possible_personal_expense", 0.85,
                             f"Description mentions '{hit}', which suggests a personal purchase.")

        for word, cat in KEYWORD_CATEGORY.items():
            if word in d and cat != item.category:
                return self._out("category_mismatch", 0.75,
                                 f"'{word}' suggests {cat}, but the claim is filed under {item.category}.")

        if item.category == "Entertainment" and not any(w in d for w in BUSINESS_WORDS):
            # deliberately low confidence -> exercises the human-review path
            return self._out("no_business_purpose", 0.45,
                             "Entertainment spend without a clear business purpose in the description.")

        return self._out("consistent", 0.80, "Description is consistent with the category.")

    @staticmethod
    def _out(label: str, confidence: float, rationale: str) -> str:
        return json.dumps({"label": label, "confidence": confidence, "rationale": rationale})
