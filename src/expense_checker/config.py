"""Settings come from environment variables (optionally via a local .env file).
No secrets live in code; .env is git-ignored and .env.example documents the keys."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
SAMPLE_DIR = ROOT / "data" / "sample"
REFERENCE_DIR = ROOT / "data" / "reference"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env reader (KEY=VALUE lines). Real env vars always win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True)
class Settings:
    db_path: str = "output/expenses.db"
    ai_provider: str = "heuristic"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ai_timeout: float = 30.0
    ai_min_confidence: float = 0.6

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        env = os.environ.get
        return cls(
            db_path=env("EXPENSE_DB_PATH", cls.db_path),
            ai_provider=env("AI_PROVIDER", cls.ai_provider).lower(),
            ollama_url=env("OLLAMA_URL", cls.ollama_url),
            ollama_model=env("OLLAMA_MODEL", cls.ollama_model),
            ai_timeout=float(env("AI_TIMEOUT_SECONDS", cls.ai_timeout)),
            ai_min_confidence=float(env("AI_MIN_CONFIDENCE", cls.ai_min_confidence)),
        )
