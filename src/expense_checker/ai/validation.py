"""Never trust model output: parse + validate against a strict schema."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .base import ALLOWED_LABELS

MAX_RATIONALE = 300


class InvalidResponse(ValueError):
    """Model output was not usable (not JSON, wrong labels, bad confidence...)."""


@dataclass(frozen=True)
class Observation:
    label: str
    confidence: float
    rationale: str


def parse_observation(raw: str) -> Observation:
    if not isinstance(raw, str) or not raw.strip():
        raise InvalidResponse("empty response")
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidResponse(f"not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise InvalidResponse("JSON is not an object")

    label = data.get("label")
    if label not in ALLOWED_LABELS:
        raise InvalidResponse(f"unsupported label {label!r}")

    conf = data.get("confidence")
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
        raise InvalidResponse(f"confidence must be a number in [0,1], got {conf!r}")

    rationale = data.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise InvalidResponse("missing rationale")

    return Observation(label=label, confidence=float(conf), rationale=rationale.strip()[:MAX_RATIONALE])
