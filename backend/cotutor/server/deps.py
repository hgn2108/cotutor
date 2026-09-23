"""Process-wide dependencies for the server. Tests swap these out with monkeypatch."""

from __future__ import annotations

from typing import Any

from ..cache import RunCache
from ..config import settings
from ..llm import GeminiClient, LLMClient
from .ratelimit import RateLimiter

cache = RunCache(settings.cache_dir)
limiter = RateLimiter(settings.runs_per_hour_per_ip)


def make_llm(user_key: str | None) -> LLMClient | None:
    """A client for the user's own key if given, else the server's shared key (if any)."""
    key = user_key or settings.gemini_api_key
    return GeminiClient(key, settings.smart_models, settings.fast_models) if key else None


def features() -> dict[str, Any]:
    return {"server_key": bool(settings.gemini_api_key),
            "models": {"smart": settings.smart_models[0], "fast": settings.fast_models[0]}}
