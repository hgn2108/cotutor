"""Score one pipeline run (its event stream) against the golden set."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from cotutor.complexity import _first_big_o, expected_slope, normalize_claim
from cotutor.config import settings
from cotutor.executor import LocalExecutor

from .golden import Golden


@dataclass
class RunScore:
    id: str
    # Correctness, judged only by the golden solution and hidden tests
    final_correct: bool | None = None
    first_draft_correct: bool | None = None
    golden_failure: str | None = None
    # What the pipeline believed and did
    verified: bool = False
    attempts: int = 0
    oracle_trusted: bool | None = None
    stress_caught: bool = False           # tests passed but random stress testing found a bug
    naive_check: str | None = None        # naive | rewritten | optimal | inconclusive | skipped
    # Teaching accuracy
    claimed_time: str | None = None
    complexity_correct: bool | None = None  # None when the claim can't be auto-scored
    measured_verdict: str | None = None
    pattern: str | None = None
    pattern_correct: bool | None = None
    lesson_complete: bool = False
    has_trace: bool = False
    has_step_counts: bool = False
    # Cost
    llm_calls: int = 0
    tokens: int = 0
    seconds: float = 0.0
    models: list[str] = field(default_factory=list)
    fell_back: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _artifacts(events: list[dict], name: str) -> list[Any]:
    return [e["data"] for e in events if e.get("type") == "artifact" and e.get("name") == name]


def _stage(events: list[dict], stage_id: str) -> dict | None:
    done = [e for e in events
            if e.get("type") == "stage" and e["id"] == stage_id and e["status"] != "running"]
    return done[-1] if done else None


async def golden_check(golden: Golden, code: str) -> tuple[bool, str | None]:
    """Run candidate code on the hidden cases; expected outputs come from the golden solution."""
    cases = [{"id": f"case{i}", "args": args} for i, args in enumerate(golden.cases)]
    res = await LocalExecutor().run({"kind": "tests", "spec": golden.spec(), "code": code,
                                     "reference_code": golden.code, "checker_code": golden.checker or None,
                                     "cases": cases}, 20)
    if not res.get("ok"):
        err = res.get("error") or {}
        return False, f"{err.get('type')}: {err.get('message', '')}"[:160]
    for c, case in zip(res["cases"], golden.cases, strict=True):
        if c["status"] != "pass":
            detail = c.get("error") or f"expected {c.get('expected')!r:.50} got {c.get('got')!r:.50}"
            return False, f"{c['status']} on {str(case)[:60]}: {detail}"[:200]
    return True, None


def complexity_matches(claimed: str, truth: str) -> bool | None:
    claim, gold = _first_big_o(claimed), _first_big_o(truth)
    a, b = expected_slope(claim), expected_slope(gold)
    if a is not None and b is not None:
        return abs(a - b) <= 0.35
    if normalize_claim(claim) == normalize_claim(gold):
        return True
    return None  # multi-variable or unusual: not auto-scorable


def _naive_label(stage: dict | None) -> str | None:
    if not stage:
        return None
    d = stage.get("detail", "")
    for key, label in (("Rewrote", "rewritten"), ("already optimal", "optimal"),
                       ("Inconclusive", "inconclusive"), ("grows faster", "naive"), ("skipped", "skipped")):
        if key in d:
            return label
    return None


async def score_run(golden: Golden, events: list[dict]) -> RunScore:
    s = RunScore(id=golden.id)
    done = [e for e in events if e.get("type") == "done"]
    summary = done[-1]["summary"] if done else {}
    s.error = summary.get("error")
    s.verified = bool(summary.get("verified"))
    s.attempts = summary.get("attempts") or 0
    s.llm_calls = summary.get("llm_calls", 0)
    s.tokens = summary.get("input_tokens", 0) + summary.get("output_tokens", 0)
    s.seconds = round(summary.get("ms", 0) / 1000, 1)
    s.models = sorted({m for e in events if e.get("type") == "stage" for m in e.get("models") or []})
    first_choice = {settings.smart_models[0], settings.fast_models[0]}
    s.fell_back = any(m not in first_choice for m in s.models)

    solutions = _artifacts(events, "solution")
    if solutions:
        s.final_correct, s.golden_failure = await golden_check(golden, solutions[-1]["code"])
        first = next((x for x in solutions if x.get("revision") == 0), solutions[0])
        s.first_draft_correct = (s.final_correct if first["code"] == solutions[-1]["code"]
                                 else (await golden_check(golden, first["code"]))[0])
        s.claimed_time = solutions[-1]["time_complexity"]
        s.complexity_correct = complexity_matches(s.claimed_time, golden.time)

    oracle = _artifacts(events, "oracle")
    s.oracle_trusted = oracle[-1]["trusted"] if oracle else None
    verifications = _artifacts(events, "verification")
    if verifications:
        first_v = verifications[0]
        tests_passed = first_v["results"] and all(r["status"] in ("pass", "ran") for r in first_v["results"])
        s.stress_caught = bool(tests_passed and first_v.get("counterexample"))
    s.naive_check = _naive_label(_stage(events, "naive_check"))

    complexity = _artifacts(events, "complexity")
    s.measured_verdict = complexity[-1]["verdict"] if complexity else None
    intro, deep = _artifacts(events, "lesson_intro"), _artifacts(events, "lesson_deep")
    if intro:
        s.pattern = intro[-1]["pattern"]
        text = s.pattern.lower()
        s.pattern_correct = any(k in text for k in golden.patterns)
    s.lesson_complete = bool(intro and deep and _artifacts(events, "explanation"))
    s.has_trace = bool(_artifacts(events, "trace"))
    s.has_step_counts = bool(_artifacts(events, "line_counts"))
    return s
