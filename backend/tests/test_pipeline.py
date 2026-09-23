from cotutor.executor import LocalExecutor
from cotutor.llm import ScriptedLLM
from cotutor.pipeline import Pipeline, PipelineConfig

from .fixtures import FIXED_CODE, two_sum_script


async def run_pipeline(script, **config):
    events = []

    async def emit(ev):
        events.append(ev)

    llm = ScriptedLLM(script)
    summary = await Pipeline(llm, LocalExecutor(), emit, PipelineConfig(**config)).run("two sum")
    return summary, events, llm


def artifacts(events, name):
    return [e["data"] for e in events if e["type"] == "artifact" and e["name"] == name]


async def test_stress_test_catches_bug_and_debugger_fixes_it():
    summary, events, llm = await run_pipeline(two_sum_script())

    assert summary["verified"] is True
    assert summary["attempts"] == 2

    first, second = artifacts(events, "verification")
    # Hand-written tests pass, but the random stress test finds the self-pairing bug.
    assert first["verified"] is False and first["counterexample"] is not None
    assert second["verified"] is True and second["stress_trials"] > 0
    # The counterexample is kept as a regression test.
    assert any(c["source"] == "stress" for c in second["cases"])
    # The debugger saw the concrete failing input.
    assert "args" in llm.calls["debugger"][0]

    assert artifacts(events, "solution")[-1]["code"] == FIXED_CODE
    assert artifacts(events, "oracle")[0]["trusted"] is True


async def test_complexity_and_trace_are_produced():
    summary, events, _ = await run_pipeline(two_sum_script())
    complexity = artifacts(events, "complexity")[0]
    assert complexity["verdict"] == "consistent"
    assert 0.6 < complexity["slope"] < 1.5

    trace = artifacts(events, "trace")[0]
    assert trace["result"] == [1, 2]
    assert any("seen" in s["locals"] for s in trace["steps"])
    assert summary["has_trace"] and summary["explained"]


async def test_malformed_generated_case_is_dropped():
    _, events, _ = await run_pipeline(two_sum_script())
    ids = {c["id"] for c in artifacts(events, "verification")[0]["cases"]}
    assert {"ex1", "ex2", "t1", "t2"} <= ids and "t3" not in ids


async def test_gives_up_after_max_attempts():
    script = two_sum_script()
    script["debugger"][0] = script["debugger"][0].model_copy(
        update={"code": script["solver"][0].code})  # "fix" that changes nothing
    summary, events, _ = await run_pipeline(script, max_debug_attempts=1)
    assert summary["verified"] is False
    assert summary["attempts"] == 2
    assert events[-1]["type"] == "done"


async def test_stage_events_are_paired():
    _, events, _ = await run_pipeline(two_sum_script())
    stages = [e for e in events if e["type"] == "stage"]
    running = {e["id"] for e in stages if e["status"] == "running"}
    finished = {e["id"] for e in stages if e["status"] != "running"}
    assert running == finished


async def test_lesson_is_built_and_grounded_in_step_counts():
    summary, events, llm = await run_pipeline(two_sum_script())
    assert summary["lesson"] is True
    intro = artifacts(events, "lesson_intro")[0]
    assert intro["bottleneck_line"] == 3 and "for j in range" in intro["brute_force_code"]
    assert sum(o["correct"] for o in intro["pattern_options"]) == 1

    counts = artifacts(events, "line_counts")[0]
    sol = [r["total"] for r in counts["solution"]]
    brute = [r["total"] for r in counts["brute_force"]]
    assert sol == sorted(sol) and brute[-1] > 10 * sol[-1]  # quadratic vs linear
    # The derivation prompt carries the measured evidence.
    assert "brute_force n=32" in llm.calls["coach_deep"][0]
    assert "Skipping x > target" in llm.calls["coach_deep"][0]  # the bug found during verification


async def test_bad_line_numbers_are_dropped():
    script = two_sum_script()
    script["coach_intro"][0] = script["coach_intro"][0].model_copy(update={"bottleneck_line": 99})
    _, events, _ = await run_pipeline(script)
    assert artifacts(events, "lesson_intro")[0]["bottleneck_line"] is None
