from __future__ import annotations

from .base import PolicyReviewer


def get_reviewer(settings) -> PolicyReviewer | None:
    """Factory: the only place that knows which concrete provider is in use."""
    provider = settings.ai_provider
    if provider == "none":
        return None
    if provider == "heuristic":
        from .heuristic import HeuristicReviewer
        return HeuristicReviewer()
    if provider == "ollama":
        from .ollama import OllamaReviewer
        return OllamaReviewer(settings.ollama_url, settings.ollama_model, settings.ai_timeout)
    raise ValueError(f"Unknown AI_PROVIDER '{provider}' (use heuristic | ollama | none)")
