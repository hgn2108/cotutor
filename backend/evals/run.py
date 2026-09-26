"""Evaluate the pipeline against the golden set.

    uv run python -m evals.run                         # score existing recordings (no LLM cost)
    uv run python -m evals.run --live                  # fresh runs of every golden problem
    uv run python -m evals.run --live --limit 10 --no-debug   # ablation: debug loop off

Writes evals/results/<name>.json (per-run scores + aggregate) and evals/results/<name>.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from cotutor import library
from cotutor.cache import DEMO_DIR
from cotutor.config import settings
from cotutor.executor import LocalExecutor
from cotutor.llm import GeminiClient
from cotutor.pipeline import KnownProblem, Pipeline, PipelineConfig

from .golden import GOLDEN, Golden
from .report import aggregate, markdown
from .score import score_run

EVALS = Path(__file__).parent
RESULTS = EVALS / "results"


def recording_for(golden: Golden) -> Path | None:
    roadmap = DEMO_DIR / "roadmap" / f"{golden.id}.json"
    if roadmap.exists():
        return roadmap
    item = library.roadmap_problem(golden.id)
    lib = library.library_match(item["title"]) if item else None
    path = DEMO_DIR / f"{lib['id']}.json" if lib else None
    return path if path and path.exists() else None


async def live_events(golden: Golden, llm, debug: bool) -> list[dict]:
    item = library.roadmap_problem(golden.id)
    known = (KnownProblem(item["class_name"]) if item["kind"] == "design"
             else KnownProblem(item["entry"], tuple(item["params"])))
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    config = PipelineConfig(max_debug_attempts=settings.max_debug_attempts if debug else 0)
    await Pipeline(llm, LocalExecutor(), emit, config).run(library.name_prompt(item), known)
    return events


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text())["events"]


def _write(name: str, payload: dict, report: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(payload, indent=1) + "\n")
    (RESULTS / f"{name}.md").write_text(report)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="run the pipeline fresh instead of scoring recordings")
    parser.add_argument("--no-debug", action="store_true",
                        help="ablation: disable the debug loop (live only)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    goldens = [g for g in GOLDEN if not args.only or g.id in args.only]
    if args.limit:
        goldens = goldens[: args.limit]
    scores = []
    if args.live:
        if not settings.gemini_api_key:
            raise SystemExit("Set GEMINI_API_KEY in .env first.")
        llm = GeminiClient(settings.gemini_api_key, settings.smart_models, settings.fast_models)
        runs_dir = EVALS / "runs" / time.strftime("%Y%m%d-%H%M%S")
        runs_dir.mkdir(parents=True, exist_ok=True)
        for g in goldens:
            events = await live_events(g, llm, debug=not args.no_debug)
            (runs_dir / f"{g.id}.json").write_text(json.dumps({"id": g.id, "events": events}))
            score = await score_run(g, events)
            scores.append(score.to_dict())
            print(f"{g.id:<50} correct={score.final_correct} verified={score.verified} {score.seconds}s")
        name = args.name or ("live-no-debug" if args.no_debug else "live")
        note = f"{len(scores)} fresh runs from problem names · models {settings.smart_models[0]} → fallbacks"
    else:
        missing = []
        for g in goldens:
            path = recording_for(g)
            if not path:
                missing.append(g.id)
                continue
            score = await score_run(g, _load(path))
            scores.append(score.to_dict())
        name = args.name or "recordings"
        note = (f"{len(scores)} recorded lessons scored against independent golden solutions"
                + (f"; {len(missing)} golden problems have no recording yet" if missing else "")
                + ". Recordings are only saved when a run verifies, so the correct and verified rates "
                "are upper bounds (survivorship). What this measures is whether *verified* can be "
                "trusted, and teaching accuracy. Live runs (`--live`) measure unbiased success rates.")

    agg = aggregate(scores)
    report = markdown(f"Evaluation: {name}", agg, note)
    _write(name, {"name": name, "aggregate": agg, "runs": scores}, report)
    print("\n" + report)


if __name__ == "__main__":
    asyncio.run(main())
