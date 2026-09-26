"""The evaluation's ground truth must itself be right."""

import pytest

from cotutor import library
from cotutor.executor import LocalExecutor
from evals.golden import GOLDEN
from evals.novel import NOVEL

ROADMAP_IDS = {p["id"] for p in library.roadmaps()["problems"]}


def test_golden_ids_are_roadmap_problems():
    assert {g.id for g in GOLDEN} <= ROADMAP_IDS
    assert len({g.id for g in GOLDEN}) == len(GOLDEN)


def test_novel_problems_have_statements_and_unique_ids():
    ids = [g.id for g in GOLDEN + NOVEL]
    assert len(set(ids)) == len(ids)
    assert all(g.statement.strip() and g.entry in g.statement for g in NOVEL)


@pytest.mark.parametrize("golden", GOLDEN + NOVEL, ids=lambda g: g.id)
async def test_golden_solution_is_correct_and_runs_every_hidden_case(golden):
    known = [{"id": f"check{i}", "args": args, "expected": exp}
             for i, (args, exp) in enumerate(golden.checks)]
    hidden = [{"id": f"case{i}", "args": args} for i, args in enumerate(golden.cases)]
    res = await LocalExecutor().run({"kind": "tests", "spec": golden.spec(), "code": golden.code,
                                     "cases": known + hidden}, 20)
    assert res["ok"], res
    statuses = {c["id"]: c["status"] for c in res["cases"]}
    assert all(statuses[c["id"]] == "pass" for c in known), res["cases"]
    assert all(statuses[c["id"]] == "ran" for c in hidden), res["cases"]


def test_complexity_scoring_is_lenient_where_it_should_be():
    from evals.score import complexity_matches

    assert complexity_matches("O(n)", "O(n)") is True
    assert complexity_matches("O(N) time, single pass", "O(n)") is True
    assert complexity_matches("O(1) per operation", "O(1)") is True
    assert complexity_matches("O(n^2)", "O(n)") is False
    assert complexity_matches("O(m * n)", "O(m n)") is True
    assert complexity_matches("O(amount * len(coins))", "O(amount * n)") is None  # not auto-scorable


async def test_scoring_catches_a_false_verification():
    """A run the pipeline called verified but that fails the golden tests must be flagged."""
    from evals.golden import BY_ID
    from evals.report import aggregate
    from evals.score import score_run

    wrong = "def maxProfit(prices):\n    return max(prices) - min(prices)\n"
    events = [
        {"type": "artifact", "name": "solution",
         "data": {"code": wrong, "revision": 0, "time_complexity": "O(n)"}},
        {"type": "done", "summary": {"verified": True, "attempts": 1, "llm_calls": 6, "ms": 12000,
                                     "input_tokens": 5000, "output_tokens": 2000}},
    ]
    score = await score_run(BY_ID["best-time-to-buy-and-sell-stock"], events)
    assert score.verified and score.final_correct is False
    agg = aggregate([score.to_dict()])
    assert agg["false_verified"] == ["best-time-to-buy-and-sell-stock"]
    assert agg["verified_precision"].startswith("0/1")


def test_rate_limited_runs_are_excluded_not_counted_wrong():
    from evals.report import aggregate

    ok = {"id": "a", "final_correct": True, "first_draft_correct": True, "verified": True,
          "complexity_correct": True, "pattern_correct": True, "pattern": "x", "naive_check": None,
          "stress_caught": False, "oracle_trusted": True, "lesson_complete": True, "llm_calls": 6,
          "tokens": 100, "seconds": 10, "fell_back": False, "golden_failure": None, "infra_error": False}
    limited = ok | {"id": "b", "final_correct": None, "verified": False, "infra_error": True}
    agg = aggregate([ok, limited])
    assert agg["runs"] == 1 and agg["infra_errors"] == ["b"] and agg["correct"].startswith("1/1")
