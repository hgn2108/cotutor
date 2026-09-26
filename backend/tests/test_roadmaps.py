"""Roadmap data integrity, name-based lessons and the signature check."""

import re

from cotutor import library
from cotutor.executor import LocalExecutor
from cotutor.llm import ScriptedLLM
from cotutor.pipeline import KnownProblem, Pipeline
from cotutor.server.session import Session

from .fixtures import SPEC, two_sum_script


def test_roadmap_lists_are_complete_and_consistent():
    data = library.roadmaps()
    probs = data["problems"]
    assert sum("neetcode150" in p["roadmaps"] for p in probs) == 150
    assert sum("blind75" in p["roadmaps"] for p in probs) == 75
    assert len({p["id"] for p in probs}) == len(probs)
    assert len({p["number"] for p in probs}) == len(probs)
    for p in probs:
        assert p["category"] in data["categories"]
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p["id"])
        assert p["url"] == f"https://leetcode.com/problems/{p['id']}/"
        if p["kind"] == "function":
            assert p["entry"] and isinstance(p["params"], list)
        assert "statement" not in p  # facts only, never problem text


def test_every_library_problem_is_on_a_roadmap():
    titles = {p["title"] for p in library.roadmaps()["problems"]}
    assert all(p["title"] in titles for p in library.problems())


def test_session_resolves_roadmap_refs():
    resolve = Session._resolve.__get__(object.__new__(Session))
    # A roadmap problem that is also in the library replays the recorded lesson.
    problem, known = resolve({"ref": "two-sum"})
    assert problem == library.library_match("Two Sum")["statement"] and known is None
    # Otherwise the lesson starts from the name and the signature is checked.
    problem, known = resolve({"ref": "koko-eating-bananas"})
    assert problem.startswith("LeetCode 875: Koko Eating Bananas")
    assert known == KnownProblem("minEatingSpeed", ("piles", "h"))
    # Design problems start from the class name.
    assert resolve({"ref": "lru-cache"}) == ("LeetCode 146: LRU Cache\nClass: LRUCache",
                                             KnownProblem("LRUCache"))
    assert "aren't supported yet" in resolve({"ref": "clone-graph"})
    assert resolve({"ref": "nope"}) == "Unknown roadmap problem."


async def test_known_signature_accepts_the_right_problem():
    summary, events, _ = await run_pipeline_known(KnownProblem("twoSum", ("nums", "target")))
    assert summary["verified"] is True


async def test_wrong_reconstruction_is_caught_before_teaching():
    summary, events, llm = await run_pipeline_known(KnownProblem("twoSum", ("numbers", "target")))
    assert summary["error"] == "signature_mismatch"
    assert any(e["type"] == "error" and e.get("code") == "unrecognized" for e in events)
    assert not llm.calls["solver"]  # nothing downstream ran


async def test_name_based_lessons_quote_the_restatement():
    _, _, llm = await run_pipeline_known(KnownProblem("twoSum", ("nums", "target")))
    assert SPEC.summary in llm.calls["coach_intro"][0]


async def run_pipeline_known(known):
    events = []

    async def emit(ev):
        events.append(ev)

    llm = ScriptedLLM(two_sum_script())
    summary = await Pipeline(llm, LocalExecutor(), emit).run("LeetCode 1: Two Sum", known)
    return summary, events, llm



def test_roadmaps_endpoint_marks_recorded_lessons():
    from fastapi.testclient import TestClient

    from cotutor.server.app import app

    probs = {p["id"]: p for p in TestClient(app).get("/api/roadmaps").json()["problems"]}
    assert probs["two-sum"]["recorded"] is True           # library recording reused
    assert probs["koko-eating-bananas"]["recorded"] is True  # recorded from its name
    assert probs["clone-graph"]["recorded"] is False  # special structure: never recorded
