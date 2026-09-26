"""Aggregate run scores into the metrics the README reports."""

from __future__ import annotations

import statistics
from typing import Any


def _rate(num: int, den: int) -> str:
    return f"{num}/{den} ({100 * num / den:.0f}%)" if den else "n/a"


def _pct(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * (len(s) - 1) + 0.5))] if s else 0.0


def aggregate(scores: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [s for s in scores if s["final_correct"] is not None]
    verified = [s for s in scored if s["verified"]]
    false_verified = [s["id"] for s in verified if not s["final_correct"]]
    drafts = [s for s in scored if s["first_draft_correct"] is not None]
    rescued = [s["id"] for s in drafts if not s["first_draft_correct"] and s["final_correct"]]
    complexity = [s for s in scored if s["complexity_correct"] is not None]
    patterns = [s for s in scored if s["pattern_correct"] is not None]
    naive: dict[str, int] = {}
    for s in scores:
        if s["naive_check"]:
            naive[s["naive_check"]] = naive.get(s["naive_check"], 0) + 1
    seconds = [s["seconds"] for s in scores if s["seconds"]]
    return {
        "runs": len(scores),
        "correct": _rate(sum(s["final_correct"] for s in scored), len(scored)),
        "verified": _rate(len(verified), len(scored)),
        "verified_precision": _rate(len(verified) - len(false_verified), len(verified)),
        "false_verified": false_verified,
        "first_draft_correct": _rate(sum(s["first_draft_correct"] for s in drafts), len(drafts)),
        "debug_rescued": rescued,
        "stress_caught": [s["id"] for s in scores if s["stress_caught"]],
        "oracle_trusted": _rate(sum(bool(s["oracle_trusted"]) for s in scores), len(scores)),
        "naive_check": naive,
        "complexity_correct": _rate(sum(s["complexity_correct"] for s in complexity), len(complexity)),
        "complexity_unscorable": len(scored) - len(complexity),
        "pattern_correct": _rate(sum(s["pattern_correct"] for s in patterns), len(patterns)),
        "pattern_misses": [f"{s['id']}: {s['pattern']}" for s in patterns if not s["pattern_correct"]],
        "lesson_complete": _rate(sum(s["lesson_complete"] for s in scores), len(scores)),
        "median_llm_calls": statistics.median([s["llm_calls"] for s in scores]) if scores else 0,
        "median_tokens": int(statistics.median([s["tokens"] for s in scores])) if scores else 0,
        "median_seconds": statistics.median(seconds) if seconds else 0,
        "p90_seconds": _pct(seconds, 0.9),
        "fell_back": _rate(sum(s["fell_back"] for s in scores), len(scores)),
        "failures": [f"{s['id']}: {s['golden_failure']}" for s in scored if not s["final_correct"]],
    }


def markdown(title: str, agg: dict[str, Any], note: str = "") -> str:
    rows = [
        ("**Correct** (hidden golden tests)", agg["correct"]),
        ("Verified by the pipeline", agg["verified"]),
        ("**Verified → actually correct** (precision)", agg["verified_precision"]),
        ("First draft correct (before debugging)", agg["first_draft_correct"]),
        ("Rescued by the debugger", str(len(agg["debug_rescued"]))),
        ("Bugs caught only by random stress testing", str(len(agg["stress_caught"]))),
        ("Brute-force oracle trusted", agg["oracle_trusted"]),
        ("Claimed Big-O matches ground truth",
         f"{agg['complexity_correct']} · {agg['complexity_unscorable']} not auto-scorable"),
        ("Coach names the right pattern", agg["pattern_correct"]),
        ("Complete lessons", agg["lesson_complete"]),
        ("Median LLM calls · tokens", f"{agg['median_llm_calls']:g} · {agg['median_tokens']:,}"),
        ("Latency median · p90", f"{agg['median_seconds']:.0f} s · {agg['p90_seconds']:.0f} s"),
        ("Runs that fell back to a lighter model", agg["fell_back"]),
    ]
    out = [f"## {title}", "", note, "" if note else "", "| Metric | Result |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    naive = ", ".join(f"{k} {v}" for k, v in sorted(agg["naive_check"].items()))
    out += ["", f"Naive-brute-force check outcomes: {naive or 'n/a'}."]
    sections = (("False verifications", agg["false_verified"]),
                ("Incorrect final solutions", agg["failures"]),
                ("Debugger rescues", agg["debug_rescued"]),
                ("Caught by stress testing", agg["stress_caught"]),
                ("Pattern misses", agg["pattern_misses"]))
    for label, items in sections:
        if items:
            out += ["", f"**{label}:**", *[f"- {x}" for x in items]]
    return "\n".join(line for line in out) + "\n"
