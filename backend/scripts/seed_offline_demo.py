"""Regenerate the bundled offline demo from the scripted Two Sum fixture.

Agent responses are scripted (labeled as such in the UI); all execution results are real.
Run from backend/:  uv run python -m scripts.seed_offline_demo
"""

import asyncio
import json

from cotutor.api import PROBLEMS
from cotutor.cache import DEMO_DIR
from cotutor.executor import LocalExecutor
from cotutor.llm import ScriptedLLM
from cotutor.pipeline import Pipeline
from tests.fixtures import two_sum_script


async def main() -> None:
    events: list[dict] = []

    async def emit(ev: dict) -> None:
        events.append(ev)

    problem = next(p for p in PROBLEMS if p["id"] == "two-sum")
    summary = await Pipeline(ScriptedLLM(two_sum_script()), LocalExecutor(), emit).run(problem["statement"])
    out = {"problem": problem["statement"], "solver": "gemini", "recording": "scripted", "events": events}
    (DEMO_DIR / "two-sum.json").write_text(json.dumps(out))
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
