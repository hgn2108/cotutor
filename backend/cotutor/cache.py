"""Record pipeline runs and replay them.

Replays make repeat questions instant and free (no LLM quota), and the bundled recordings in
``data/demos`` keep the demo working even with no API key configured.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .pipeline import Emit

DEMO_DIR = Path(__file__).parent / "data" / "demos"


def cache_key(problem: str) -> str:
    norm = re.sub(r"\s+", " ", problem.strip().lower())
    return hashlib.sha256(norm.encode()).hexdigest()[:24]


class RunCache:
    def __init__(self, directory: Path):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self._demos: dict[str, Path] = {}
        for path in sorted(DEMO_DIR.glob("*.json")):
            rec = json.loads(path.read_text())
            self._demos[cache_key(rec["problem"])] = path

    def get(self, problem: str) -> dict[str, Any] | None:
        key = cache_key(problem)
        for path in (self.dir / f"{key}.json", self._demos.get(key)):
            if path and path.exists():
                return json.loads(path.read_text())
        return None

    def put(self, problem: str, events: list[dict[str, Any]], meta: dict | None = None) -> None:
        if not events or events[-1].get("type") != "done":
            return
        if not events[-1]["summary"].get("verified"):
            return  # only cache runs worth showing again
        record = {"problem": problem, "events": events, **(meta or {})}
        (self.dir / f"{cache_key(problem)}.json").write_text(json.dumps(record))


async def replay(record: dict[str, Any], emit: Emit, total_s: float = 4.0) -> None:
    """Re-emit a recorded run, paced so the agent timeline still reads naturally."""
    events = record["events"]
    running = sum(1 for e in events if e.get("type") == "stage" and e["status"] == "running")
    delay = total_s / max(running, 1)
    for ev in events:
        if ev.get("type") == "done":
            ev = ev | {"summary": ev["summary"] | {"replayed": True,
                                                   "recording": record.get("recording", "cache")}}
        await emit(ev)
        if ev.get("type") == "stage" and ev["status"] == "running":
            await asyncio.sleep(delay)
