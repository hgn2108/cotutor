"""Record live pipeline runs so lessons replay instantly and for free.

    uv run python -m cotutor.record                          # every library problem
    uv run python -m cotutor.record two-sum                  # specific library ids
    uv run python -m cotutor.record --roadmap blind75        # roadmap problems not yet recorded
    uv run python -m cotutor.record --roadmap blind75 --limit 10

Roadmap lessons are recorded from the problem's name and signature (never its statement),
exactly as the server runs them, so the cache key matches and replays are used.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from . import library
from .cache import DEMO_DIR
from .config import settings
from .executor import LocalExecutor
from .llm import GeminiClient, LLMClient
from .pipeline import KnownProblem, Pipeline, PipelineConfig

ROADMAP_DIR = DEMO_DIR / "roadmap"


async def record(title: str, problem: str, known: KnownProblem | None, out: Path, llm: LLMClient) -> bool:
    print(f"• {title}")
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)
        if ev["type"] == "stage" and ev["status"] != "running":
            print(f"  [{ev['status']:>7}] {ev['label']}: {ev.get('detail', '')[:90]}")

    config = PipelineConfig(max_debug_attempts=settings.max_debug_attempts)
    summary = await Pipeline(llm, LocalExecutor(), emit, config).run(problem, known)
    if not summary.get("verified") or not summary.get("lesson"):
        why = summary.get("error") or ("lesson incomplete" if summary.get("verified") else "not verified")
        print(f"  not saved ({why})")
        for line in failure_details(events):
            print(f"    {line}")
        return False
    _save(out, {"problem": problem, "recording": "live",
                "models": settings.smart_models + settings.fast_models, "events": events})
    return True


def failure_details(events: list[dict]) -> list[str]:
    """Why the last verification failed, so flaky runs can be diagnosed afterwards."""
    runs = [e["data"] for e in events if e.get("type") == "artifact" and e["name"] == "verification"]
    if not runs:
        return []
    last = runs[-1]
    cases = {c["id"]: c for c in last["cases"]}
    lines = [f"load error: {last['load_error']}"] if last.get("load_error") else []
    for r in last["results"]:
        if r["status"] in ("fail", "error", "timeout"):
            args = json.dumps(cases.get(r["id"], {}).get("args"))[:80]
            detail = r.get("error") or f"expected {r.get('expected')!r:.60} got {r.get('got')!r:.60}"
            lines.append(f"{r['id']} [{r['status']}] args={args} {detail}")
    if last.get("counterexample"):
        lines.append(f"counterexample: {json.dumps(last['counterexample'])[:200]}")
    return lines[:6]


def _save(out: Path, recording: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recording))


def library_jobs(ids: list[str]):
    for p in library.problems():
        if not ids or p["id"] in ids:
            yield p["title"], p["statement"], None, DEMO_DIR / f"{p['id']}.json"


def roadmap_jobs(roadmap: str, ids: list[str]):
    """Supported roadmap problems without a recording (library matches already have one)."""
    for item in library.roadmaps()["problems"]:
        out = ROADMAP_DIR / f"{item['id']}.json"
        if (roadmap not in item["roadmaps"] or item["kind"] != "function"
                or library.library_match(item["title"]) or (ids and item["id"] not in ids)
                or (not ids and out.exists())):
            continue
        known = KnownProblem(item["entry"], tuple(item["params"]))
        yield f"{item['number']}. {item['title']}", library.name_prompt(item), known, out


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--roadmap", choices=[r["id"] for r in library.roadmaps()["roadmaps"]])
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    if not settings.gemini_api_key:
        raise SystemExit("Set GEMINI_API_KEY in .env first.")
    llm = GeminiClient(settings.gemini_api_key, settings.smart_models, settings.fast_models)
    jobs = list(roadmap_jobs(args.roadmap, args.ids) if args.roadmap else library_jobs(args.ids))
    if args.limit:
        jobs = jobs[: args.limit]
    ok = 0
    for job in jobs:
        ok += await record(*job, llm)
    print(f"\nSaved {ok}/{len(jobs)} recordings")


if __name__ == "__main__":
    asyncio.run(main())
