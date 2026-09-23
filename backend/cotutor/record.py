"""Record live pipeline runs for the problem library so the demo works offline.

    uv run python -m cotutor.record            # every library problem
    uv run python -m cotutor.record two-sum    # specific ids
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .api import PROBLEMS
from .cache import DEMO_DIR
from .config import settings
from .executor import LocalExecutor
from .llm import GeminiClient
from .pipeline import Pipeline, PipelineConfig


async def record(problem: dict, llm) -> bool:
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)
        if ev["type"] == "stage" and ev["status"] != "running":
            print(f"  [{ev['status']:>7}] {ev['label']}: {ev.get('detail', '')[:90]}")

    summary = await Pipeline(llm, LocalExecutor(), emit,
                             PipelineConfig(max_debug_attempts=settings.max_debug_attempts)
                             ).run(problem["statement"])
    if not summary.get("verified"):
        print(f"  not verified; not saved ({summary.get('error', '')})")
        return False
    out = {"problem": problem["statement"], "solver": "gemini", "recording": "live",
           "models": [settings.smart_model, settings.fast_model], "events": events}
    (DEMO_DIR / f"{problem['id']}.json").write_text(json.dumps(out))
    return True


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*")
    args = parser.parse_args()
    if not settings.gemini_api_key:
        raise SystemExit("Set GEMINI_API_KEY in .env first.")
    llm = GeminiClient(settings.gemini_api_key, settings.smart_model, settings.fast_model)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    chosen = [p for p in PROBLEMS if not args.ids or p["id"] in args.ids]
    ok = 0
    for p in chosen:
        print(f"• {p['title']}")
        ok += await record(p, llm)
    print(f"\nSaved {ok}/{len(chosen)} recordings to {DEMO_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
