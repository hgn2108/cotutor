"""Orchestrates the agents into a verify-before-you-trust pipeline.

    analyze ─┬─ design tests ─┐                ┌─ coach: pattern, brute force, bottleneck
             └─ solve ────────┴───────────────┤
                                               └─ validate oracle ─ verify ⟲ debug ─┐
        ┌──────────────────────────────────────────────────────────────────────────┘
        ├─ explain (flowchart, viz plan) ─────────────────────── trace
        └─ measure growth ─ count steps per line ─ coach: why this complexity

Every step emits events (stage progress + artifacts) through ``emit`` so the UI can render
the agents' work live. Code only ever runs through the ``Executor`` tool.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from . import agents
from .complexity import check as check_complexity
from .executor import Executor
from .llm import LLMClient, LLMError, Usage
from .schemas import ProblemSpec, Solution, TestPlan

Emit = Callable[[dict[str, Any]], Awaitable[None]]
FAILING = {"fail", "error", "timeout"}


@dataclass
class PipelineConfig:
    max_debug_attempts: int = 3
    exec_timeout_s: float = 8.0
    differential_trials: int = 300


@dataclass
class RunStats:
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    started: float = field(default_factory=time.perf_counter)


class Stage:
    """Async context manager that reports a pipeline stage's lifecycle to the UI."""

    def __init__(self, run: Pipeline, stage_id: str, label: str):
        self.run, self.id, self.label = run, stage_id, label
        self.detail, self.status = "", None
        self.tokens, self.models = 0, set()

    def note(self, detail: str, status: str | None = None) -> None:
        self.detail = detail
        if status:
            self.status = status

    def usage(self, u: Usage) -> None:
        self.tokens += u.input_tokens + u.output_tokens
        self.models.add(u.model)
        self.run.stats.input_tokens += u.input_tokens
        self.run.stats.output_tokens += u.output_tokens
        self.run.stats.llm_calls += 1

    async def __aenter__(self) -> Stage:
        self._t0 = time.perf_counter()
        await self.run.emit({"type": "stage", "id": self.id, "label": self.label,
                             "status": "running"})
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if isinstance(exc, asyncio.CancelledError):
            status, self.detail = "skipped", self.detail or "Stopped because another step failed."
        else:
            status = "failed" if exc else (self.status or "done")
            if exc and not self.detail:
                self.detail = str(exc)[:300]
        await self.run.emit({
            "type": "stage", "id": self.id, "label": self.label, "status": status,
            "detail": self.detail, "ms": round((time.perf_counter() - self._t0) * 1000),
            "tokens": self.tokens, "models": sorted(self.models),
        })


def _parse_args(raw: str) -> list | None:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, list) else None


def _harness_spec(spec: ProblemSpec) -> dict[str, Any]:
    return {
        "entry": spec.entry,
        "params": [p.model_dump() for p in spec.params],
        "comparison": spec.comparison,
        "in_place_arg": spec.in_place_arg if spec.in_place_arg >= 0 else None,
    }


class Pipeline:
    def __init__(self, llm: LLMClient, executor: Executor, emit: Emit,
                 config: PipelineConfig | None = None, solver: Any = None):
        self.llm, self.executor, self.emit = llm, executor, emit
        self.config = config or PipelineConfig()
        # Optional alternative solver (e.g. the fine-tuned Llama); must match agents.solve.
        self.solver = solver or agents.solve
        self.stats = RunStats()

    def stage(self, stage_id: str, label: str) -> Stage:
        return Stage(self, stage_id, label)

    async def artifact(self, name: str, data: Any) -> None:
        await self.emit({"type": "artifact", "name": name, "data": data})

    async def execute(self, job: dict[str, Any]) -> dict[str, Any]:
        return await self.executor.run(job, self.config.exec_timeout_s)

    # ------------------------------------------------------------------------------------
    async def run(self, problem: str) -> dict[str, Any]:
        try:
            summary = await self._run(problem)
        except LLMError as exc:
            summary = {"verified": False, "error": str(exc)}
            await self.emit({"type": "error", "message": str(exc)})
        summary |= {
            "input_tokens": self.stats.input_tokens, "output_tokens": self.stats.output_tokens,
            "llm_calls": self.stats.llm_calls,
            "ms": round((time.perf_counter() - self.stats.started) * 1000),
        }
        await self.emit({"type": "done", "summary": summary})
        return summary

    async def _run(self, problem: str) -> dict[str, Any]:
        async with self.stage("analyze", "Analyst: understand the problem") as st:
            spec, u = await agents.analyze(self.llm, problem)
            st.usage(u)
            if not spec.is_solvable:
                st.note("This doesn't look like a well-defined coding problem.", "failed")
            else:
                st.note(f"{spec.title} · {spec.difficulty} · {', '.join(spec.pattern_tags)}")
        await self.artifact("spec", spec.model_dump())
        if not spec.is_solvable:
            await self.emit({"type": "error", "message": "Please describe a coding problem with "
                             "clear inputs and outputs."})
            return {"verified": False, "error": "not_a_problem"}

        # Test design and solving are independent, so the two agents work in parallel.
        plan, solution = await asyncio.gather(self._design_tests(spec), self._solve(spec))
        await self.artifact("solution", solution.model_dump() | {"revision": 0})

        plan, brute_is_optimal = await self._ensure_naive_reference(spec, plan, solution)

        # The first half of the lesson only needs the spec, the brute force and the approach,
        # so the Coach teaches while verification is still running.
        intro_task = asyncio.create_task(
            self._coach_intro(problem, spec, solution, plan, brute_is_optimal))
        explain_task: asyncio.Task | None = None
        try:
            cases, oracle = await self._validate_oracle(spec, plan)
            solution, verification = await self._verify_and_debug(spec, plan, solution, cases, oracle)

            explain_task = asyncio.create_task(self._explain(spec, solution))
            complexity = await self._complexity(spec, plan, solution)
            counts = await self._line_counts(spec, plan, solution)
            deep = await self._coach_deep(spec, plan, solution, complexity, counts,
                                          verification["bugs"])
            explanation = await explain_task
            trace = await self._trace(spec, solution, explanation)
            intro = await intro_task
        finally:
            for task in (intro_task, explain_task):
                if task and not task.done():
                    task.cancel()

        return {
            "verified": verification["verified"],
            "attempts": verification["attempts"],
            "tests_passed": verification["passed"], "tests_total": verification["total"],
            "stress_trials": verification["trials"],
            "complexity_verdict": complexity.get("verdict") if complexity else None,
            "has_trace": bool(trace and trace.get("steps")),
            "explained": explanation is not None,
            "lesson": intro is not None and deep is not None,
        }

    # ------------------------------------------------------------------------------------
    async def _design_tests(self, spec: ProblemSpec) -> TestPlan:
        async with self.stage("design_tests", "Test Designer: edge cases + brute-force oracle") as st:
            plan, u = await agents.design_tests(self.llm, spec)
            st.usage(u)
            st.note(f"{len(plan.cases)} targeted inputs, brute-force reference, random input "
                    f"generator{', custom answer checker' if plan.checker_code.strip() else ''}")
        await self.artifact("test_plan", plan.model_dump())
        return plan

    async def _solve(self, spec: ProblemSpec) -> Solution:
        async with self.stage("solve", "Solver: design the algorithm") as st:
            solution, u = await self.solver(self.llm, spec)
            st.usage(u)
            st.note(f"{solution.approach} · claims {solution.time_complexity} time")
        return solution

    async def _validate_oracle(self, spec: ProblemSpec, plan: TestPlan):
        """Build the test suite, and only trust the reference/checker if they pass the examples."""
        cases: list[dict[str, Any]] = []
        for i, ex in enumerate(spec.examples, 1):
            args = _parse_args(ex.args_json)
            try:
                expected = json.loads(ex.expected_json)
            except json.JSONDecodeError:
                continue
            if args is not None:
                cases.append({"id": f"ex{i}", "args": args, "expected": expected,
                              "source": "example", "label": f"Example {i}"})
        for i, draft in enumerate(plan.cases, 1):
            args = _parse_args(draft.args_json)
            if args is not None:
                cases.append({"id": f"t{i}", "args": args, "source": "reference",
                              "label": draft.name, "category": draft.category,
                              "rationale": draft.rationale})

        oracle = {"trusted": False, "reference_code": plan.reference_solution,
                  "checker_code": plan.checker_code.strip() or None}
        async with self.stage("oracle", "Verify the verifier: check oracle on examples") as st:
            examples = [c for c in cases if c["source"] == "example"]
            if not examples:
                st.note("No parseable examples; generated cases can only catch crashes.",
                        "warning")
            else:
                res = await self.execute({
                    "kind": "tests", "spec": _harness_spec(spec), "code": plan.reference_solution,
                    "checker_code": oracle["checker_code"], "cases": _strip(examples),
                })
                ok = res.get("ok") and all(c["status"] == "pass" for c in res["cases"])
                oracle["trusted"] = bool(ok)
                if ok:
                    st.note(f"Brute-force oracle matches all {len(examples)} examples; "
                            "using it to compute expected outputs.")
                else:
                    st.note("Oracle disagreed with the examples, so only the examples are "
                            "checked for correctness.", "warning")
        await self.artifact("oracle", {"trusted": oracle["trusted"],
                                       "has_checker": bool(oracle["checker_code"])})
        return cases, oracle

    async def _verify_and_debug(self, spec, plan, solution, cases, oracle):
        hspec = _harness_spec(spec)
        by_id = {c["id"]: c for c in cases}
        history: list[str] = []
        diagnoses: list[str] = []
        verified, trials, passed = False, 0, 0
        attempt = 0
        for attempt in range(self.config.max_debug_attempts + 1):
            label = "Verifier: run tests" if attempt == 0 else f"Verifier: re-test fix #{attempt}"
            async with self.stage(f"verify_{attempt}", label) as st:
                job = {"kind": "tests", "spec": hspec, "code": solution.code,
                       "cases": _strip(list(by_id.values()))}
                if oracle["trusted"]:
                    job |= {"reference_code": oracle["reference_code"],
                            "checker_code": oracle["checker_code"]}
                res = await self.execute(job)
                results = res.get("cases", []) if res.get("ok") else []
                failures = [r for r in results if r["status"] in FAILING]
                if not res.get("ok"):
                    failures = [{"id": "load", "status": "error", "error": res.get("error")}]
                passed = sum(r["status"] in ("pass", "ran") for r in results)
                counterexample = None
                if not failures and oracle["trusted"] and plan.generator_code.strip():
                    diff = await self.execute({
                        "kind": "differential", "spec": hspec, "code": solution.code,
                        "reference_code": oracle["reference_code"],
                        "checker_code": oracle["checker_code"],
                        "generator_code": plan.generator_code,
                        "trials": self.config.differential_trials, "seed": attempt,
                    })
                    trials = diff.get("trials", 0) if diff.get("ok") else 0
                    counterexample = diff.get("counterexample") if diff.get("ok") else None
                    if counterexample:
                        cid = f"stress{attempt + 1}"
                        # Keep it as a regression test for every later attempt.
                        by_id[cid] = {"id": cid, "args": counterexample["args"],
                                      "source": "stress", "label": "Found by random stress test"}
                        failures = [{"id": cid, "status": "fail" if "got" in counterexample
                                     else "error", **counterexample}]
                verified = not failures
                if counterexample:
                    note = (f"{passed}/{len(results)} tests pass, but random stress testing found a "
                            f"counterexample after {trials} trials")
                else:
                    note = f"{passed}/{len(results)} tests pass" + (
                        f", {trials} random stress trials agree with the oracle" if trials else "")
                    if failures:
                        note += f" ({len(failures)} failing)"
                st.note(note, "done" if verified else "failed")
            await self.artifact("verification", {
                "attempt": attempt, "verified": verified, "results": results,
                "cases": list(by_id.values()), "stress_trials": trials,
                "counterexample": counterexample, "load_error": None if res.get("ok")
                else res.get("error"),
            })
            if verified or attempt == self.config.max_debug_attempts:
                break

            async with self.stage(f"debug_{attempt + 1}", f"Debugger: fix attempt #{attempt + 1}") as st:
                detailed = [{**by_id.get(f["id"], {}), **f} for f in failures[:4]]
                for d in detailed:
                    d.pop("rationale", None)
                fix, u = await agents.debug(self.llm, spec, solution, detailed, history)
                st.usage(u)
                disputable = [f["id"] for f in failures
                              if by_id.get(f["id"], {}).get("source") in ("reference", "stress")]
                if fix.blame == "test" and disputable:
                    for cid in disputable:
                        by_id.pop(cid, None)
                    st.note(f"Disputed {len(disputable)} oracle-generated test(s): {fix.diagnosis}")
                else:
                    before = solution.code
                    solution = solution.model_copy(update={"code": fix.code})
                    history.append(fix.fix_summary)
                    diagnoses.append(fix.diagnosis)
                    st.note(fix.diagnosis)
                    await self.artifact("debug_attempt", {
                        "attempt": attempt + 1, "diagnosis": fix.diagnosis,
                        "fix_summary": fix.fix_summary, "before": before, "after": fix.code,
                        "failures": detailed,
                    })
                    await self.artifact("solution", solution.model_dump() | {"revision": attempt + 1})
        return solution, {"verified": verified, "attempts": attempt + 1, "passed": passed,
                          "total": len(by_id), "trials": trials, "bugs": diagnoses}

    async def _complexity(self, spec, plan, solution) -> dict[str, Any] | None:
        if not plan.generator_code.strip():
            return None
        async with self.stage("complexity", "Profiler: measure growth rate") as st:
            res = await self.execute({"kind": "complexity", "spec": _harness_spec(spec),
                                      "code": solution.code, "generator_code": plan.generator_code})
            if not res.get("ok"):
                st.note("Could not time the solution on generated inputs.", "warning")
                return None
            chk = check_complexity(solution.time_complexity, res.get("slope"))
            st.note(chk.note, "done" if chk.verdict in ("consistent", "inconclusive") else "warning")
            data = {"points": res["points"], "slope": res.get("slope"), "claimed": chk.claimed,
                    "expected_slope": chk.expected_slope, "verdict": chk.verdict, "note": chk.note,
                    "used_worst_case": res.get("used_worst_case", False)}
        await self.artifact("complexity", data)
        return data

    async def _step_growth(self, spec, code: str, generator: str) -> float | None:
        """Growth exponent from exact step counts: log2(steps(2n) / steps(n)) at the largest n."""
        res = await self.execute({"kind": "line_counts", "spec": _harness_spec(spec), "code": code,
                                  "generator_code": generator, "sizes": [8, 16, 32, 64]})
        runs = [r for r in res.get("runs", []) if not r["capped"]] if res.get("ok") else []
        if len(runs) < 2 or runs[-2]["total"] <= 0:
            return None
        return math.log2(runs[-1]["total"] / runs[-2]["total"])

    async def _ensure_naive_reference(self, spec, plan: TestPlan, solution: Solution):
        """The brute force doubles as the lesson's starting point, so it must actually be naive.

        Step counts on doubling inputs tell us. If the reference grows no faster than the
        solution, the Test Designer gets one retry with that feedback. If it still doesn't,
        the problem simply has no slower obvious approach and the lesson says so.
        """
        if not plan.generator_code.strip():
            return plan, False
        async with self.stage("naive_check", "Check the brute force is really brute force") as st:
            sol = await self._step_growth(spec, solution.code, plan.generator_code)
            ref = await self._step_growth(spec, plan.reference_solution, plan.generator_code)
            if sol is None or ref is None or ref >= sol + 0.5:
                st.note("Brute force grows faster than the solution, as a starting point should."
                        if sol is not None and ref is not None else "Could not measure; skipped.")
                return plan, False
            st.note(f"Reference grows like n^{ref:.1f}, same as the solution. Asking for a naive one.",
                    "warning")
            feedback = (
                f"Your reference solution is not naive: measured step counts grow like n^{ref:.1f}, "
                f"the same as the optimized solution ({solution.approach}). Write a brute force that "
                "enumerates candidates directly, without that technique. Keep the same generator "
                "and checker behaviour."
            )
            try:
                retry, u = await agents.design_tests(self.llm, spec, feedback)
                st.usage(u)
            except LLMError:
                return plan, True
            ref2 = await self._step_growth(spec, retry.reference_solution, retry.generator_code
                                           or plan.generator_code)
            if ref2 is not None and ref2 >= sol + 0.5:
                st.note(f"Rewrote the brute force: it now grows like n^{ref2:.1f} vs n^{sol:.1f}.")
                await self.artifact("test_plan", retry.model_dump())
                return retry, False
            st.note("No slower straightforward approach exists; the direct approach is already optimal.")
            return plan, True

    async def _coach_intro(self, problem, spec, solution, plan, brute_is_optimal=False):
        try:
            async with self.stage("coach_intro", "Coach: pattern, brute force and its bottleneck") as st:
                intro, u = await agents.coach_intro(self.llm, problem, spec, solution,
                                                    plan.reference_solution, brute_is_optimal)
                st.usage(u)
                st.note(f"Pattern: {intro.pattern} · {len(intro.bottleneck_hints)} hints")
        except LLMError:
            return None
        data = intro.model_dump()
        n_lines = len(plan.reference_solution.rstrip().split("\n"))
        if not 1 <= data["bottleneck_line"] <= n_lines:
            data["bottleneck_line"] = None
        if sum(o["correct"] for o in data["pattern_options"]) != 1:
            # Keep the quiz gradeable: the named pattern is the answer.
            for o in data["pattern_options"]:
                o["correct"] = o["name"].strip().lower() == intro.pattern.strip().lower()
            if not any(o["correct"] for o in data["pattern_options"]):
                data["pattern_options"].append({"name": intro.pattern, "correct": True,
                                                "feedback": intro.pattern_summary})
        data["brute_force_code"] = plan.reference_solution
        data["brute_is_optimal"] = brute_is_optimal
        if brute_is_optimal:
            data["bottleneck_line"] = None
        await self.artifact("lesson_intro", data)
        return data

    async def _line_counts(self, spec, plan, solution) -> dict[str, Any] | None:
        if not plan.generator_code.strip():
            return None
        async with self.stage("line_counts", "Profiler: count how often each line runs") as st:
            out: dict[str, Any] = {}
            for name, code in (("solution", solution.code), ("brute_force", plan.reference_solution)):
                res = await self.execute({"kind": "line_counts", "spec": _harness_spec(spec),
                                          "code": code, "generator_code": plan.generator_code,
                                          "sizes": [4, 8, 16, 32]})
                if res.get("ok") and res.get("runs"):
                    out[name] = res["runs"]
                    out["used_worst_case"] = res.get("used_worst_case", False)
            if "solution" not in out:
                st.note("Could not count steps.", "warning")
                return None
            sizes = [r["n"] for r in out["solution"]]
            totals = lambda runs: " → ".join(str(r["total"]) for r in runs)  # noqa: E731
            st.note(f"n = {', '.join(map(str, sizes))}: {totals(out['solution'])} steps"
                    + (f" (brute force: {totals(out['brute_force'])})" if "brute_force" in out else ""))
        await self.artifact("line_counts", out)
        return out

    async def _coach_deep(self, spec, plan, solution, complexity, counts, bugs):
        lines = []
        for name in ("solution", "brute_force"):
            for run in (counts or {}).get(name, []):
                per_line = ", ".join(f"line {k}: {v}" for k, v in run["counts"].items())
                lines.append(f"{name} n={run['n']}: {run['total']} steps ({per_line})")
        if complexity and complexity.get("slope") is not None:
            lines.append(f"Wall-clock growth on large inputs: n^{complexity['slope']:.2f} "
                         f"({complexity['verdict'].replace('_', ' ')})")
        try:
            async with self.stage("coach_deep", "Coach: why the complexity is what it is") as st:
                deep, u = await agents.coach_deep(self.llm, spec, solution, plan.reference_solution,
                                                  "\n".join(lines) or "none", bugs)
                st.usage(u)
                st.note(f"{len(deep.derivation)} line-level costs · takeaway ready")
        except LLMError:
            return None
        data = deep.model_dump()
        n_lines = len(solution.code.rstrip().split("\n"))
        data["derivation"] = [d for d in data["derivation"] if 1 <= d["line"] <= n_lines]
        data["code"] = solution.code
        await self.artifact("lesson_deep", data)
        return data

    async def _explain(self, spec, solution):
        try:
            async with self.stage("explain", "Tutor: build the visual explanation") as st:
                explanation, u = await agents.explain(self.llm, spec, solution)
                st.usage(u)
                st.note(f"{len(explanation.flow_nodes)}-node flowchart, "
                        f"{len(explanation.viz_vars)} variables to animate")
        except LLMError:
            return None  # the solution is still useful without narration
        await self.artifact("explanation", explanation.model_dump())
        return explanation

    async def _trace(self, spec, solution, explanation):
        args = _parse_args(explanation.viz_args_json) if explanation else None
        if args is None:
            args = next((_parse_args(e.args_json) for e in spec.examples
                         if _parse_args(e.args_json) is not None), None)
        if args is None:
            return None
        async with self.stage("trace", "Tracer: record execution for animation") as st:
            res = await self.execute({"kind": "trace", "spec": _harness_spec(spec),
                                      "code": solution.code, "args": args, "max_steps": 600})
            if not res.get("ok"):
                st.note("Tracing failed.", "warning")
                return None
            st.note(f"{len(res['steps'])} execution steps recorded"
                    + (" (truncated)" if res.get("truncated") else ""))
        await self.artifact("trace", res | {"args": args, "code": solution.code})
        return res


def _strip(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only send the harness what it needs."""
    keep = ("id", "args", "expected")
    return [{k: c[k] for k in keep if k in c} for c in cases]
