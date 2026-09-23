from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv()


def _csv(name: str, default: str) -> list[str]:
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    # "smart" models do the reasoning-heavy work; "fast" ones handle cheap structuring steps.
    # Each is a fallback chain: later models are used when earlier ones are overloaded.
    smart_models: list[str] = field(default_factory=lambda: _csv(
        "COTUTOR_SMART_MODELS",
        "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite"))
    fast_models: list[str] = field(default_factory=lambda: _csv(
        "COTUTOR_FAST_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite"))

    max_debug_attempts: int = int(os.getenv("COTUTOR_MAX_DEBUG_ATTEMPTS", "3"))
    exec_timeout_s: float = float(os.getenv("COTUTOR_EXEC_TIMEOUT_S", "8"))
    runs_per_hour_per_ip: int = int(os.getenv("COTUTOR_RUNS_PER_HOUR", "20"))
    cache_dir: Path = Path(os.getenv("COTUTOR_CACHE_DIR", Path(__file__).parent / "data" / "cache"))
    allowed_origins: list[str] = field(
        default_factory=lambda: _csv("COTUTOR_ALLOWED_ORIGINS", "http://localhost:5173")
    )


settings = Settings()
