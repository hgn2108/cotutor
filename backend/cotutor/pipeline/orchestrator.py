"""Orchestrates the agents into a verify-before-you-teach pipeline.

    analyze ─┬─ design tests ─┬─ naive check ─┬─ coach: pattern, brute force, bottleneck
             └─ solve ────────┘               └─ validate oracle ─ verify ⟲ debug ─┐
        ┌──────────────────────────────────────────────────────────────────────────┘
        ├─ tutor: flowchart, animation plan ───────────────────────────── trace
        └─ growth at scale ─ step counts per line ─ coach: why this complexity

Every step emits events (stage progress + artifacts) through ``emit`` so the UI can render
the agents' work live. Code only ever runs through the ``Executor`` tool.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .. import agents
from ..executor import Executor
from ..llm import LLMClient, LLMError
from ..schemas import ProblemSpec, Solution, TestPlan
from .context import Emit, PipelineConfig, RunContext
from .profiling import Profiler
from .teaching import Teacher
from .verification import Verifier

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnownProblem:
    """A problem identified by name (e.g. from a roadmap) with its real signature.

    The lesson is reconstructed from the name, so the signature is the ground truth used to
    confirm the Analyst reconstructed the right problem before anything is taught.
    """

    entry: str                           # function name, or class name for design problems
    params: tuple[str, ...] | None = None  # None for design problems

    def matches(self, spec: ProblemSpec) -> bool:
        if self.params is None:
            return spec.kind == "design" and spec.entry == self.entry
        return spec.entry == self.entry and tuple(p.name for p in spec.params) == self.params


class Pipeline:
    def __init__(self, llm: LLMClient, executor: Executor, emit: Emit,
                 config: PipelineConfig | None = None):
        self.ctx = RunContext(llm, executor, emit, config or PipelineConfig())
        self.verifier = Verifier(self.ctx)
        self.profiler = Profiler(self.ctx)
        self.teacher = Teacher(self.ctx)

    async def run(self, problem: str, known: KnownProblem | None = None) -> dict[str, Any]:
        """Run end to end. Always finishes with a ``done`` event, even on failure."""
        try:
            summary = await self._run(problem, known)
        except LLMError as exc:
            summary = {"verified": False, "error": str(exc)}
            await self.ctx.emit({"type": "error", "message": str(exc)})
        except Exception as exc:  # never leave the UI waiting on a run that died
            log.exception("pipeline crashed")
            summary = {"verified": False, "error": f"Internal error: {type(exc).__name__}"}
            await self.ctx.emit({"type": "error", "message": "Something went wrong on our side. "
                                 "Please try again."})
        stats = self.ctx.stats
        summary |= {"input_tokens": stats.input_tokens, "output_tokens": stats.output_tokens,
                    "llm_calls": stats.llm_calls, "ms": stats.elapsed_ms()}
        await self.ctx.emit({"type": "done", "summary": summary})
        return summary

    async def _run(self, problem: str, known: KnownProblem | None) -> dict[str, Any]:
        spec = await self._analyze(problem)
        if not spec.is_solvable:
            await self.ctx.emit({"type": "error", "message": "Please describe a coding problem "
                                 "with clear inputs and outputs."})
            return {"verified": False, "error": "not_a_problem"}
        if known and not known.matches(spec):
            await self.ctx.emit({"type": "error", "code": "unrecognized", "message":
                                 "Couldn't reconstruct this problem reliably from its name. Paste "
                                 "the problem statement to get a lesson for it."})
            return {"verified": False, "error": "signature_mismatch"}
        # Signal phrases must quote text the learner sees: the original statement, or for a
        # problem given by name, the Analyst's own restatement.
        statement = spec.summary if known else problem

        # Test design and solving are independent, so the two agents work in parallel.
        plan, solution = await asyncio.gather(self._design_tests(spec), self._solve(spec))
        await self.ctx.artifact("solution", solution.model_dump() | {"revision": 0})
        reference = await self.profiler.ensure_naive_reference(spec, plan, solution)
        plan = reference.plan

        # The first half of the lesson only needs the spec, the brute force and the approach,
        # so the Coach teaches while verification is still running.
        intro_task = asyncio.create_task(
            self.teacher.lesson_intro(statement, spec, solution, plan, reference.brute_is_optimal))
        explain_task: asyncio.Task | None = None
        try:
            cases = self.verifier.build_cases(spec, plan)
            oracle = await self.verifier.validate_oracle(spec, plan, cases)
            result = await self.verifier.verify_and_debug(spec, plan, solution, cases, oracle)
            solution = result.solution

            explain_task = asyncio.create_task(self.teacher.explanation(spec, solution))
            complexity = await self.profiler.growth_at_scale(spec, plan, solution)
            counts = await self.profiler.lesson_step_counts(spec, plan, solution)
            deep = await self.teacher.lesson_deep(spec, plan, solution, complexity, counts, result.bugs)
            explanation = await explain_task
            trace = await self.teacher.trace(spec, solution, explanation)
            intro = await intro_task
        finally:
            for task in (intro_task, explain_task):
                if task and not task.done():
                    task.cancel()

        return {
            "verified": result.verified,
            "attempts": result.attempts,
            "tests_passed": result.passed, "tests_total": result.total,
            "stress_trials": result.stress_trials,
            "complexity_verdict": complexity.get("verdict") if complexity else None,
            "has_trace": bool(trace and trace.get("steps")),
            "explained": explanation is not None,
            "lesson": intro is not None and deep is not None,
        }

    async def _analyze(self, problem: str) -> ProblemSpec:
        async with self.ctx.stage("analyze", "Analyst: understand the problem") as st:
            spec, u = await agents.analyze(self.ctx.llm, problem)
            st.usage(u)
            if spec.is_solvable:
                st.note(f"{spec.title} · {spec.difficulty} · {', '.join(spec.pattern_tags)}")
            else:
                st.note("This doesn't look like a well-defined coding problem.", "failed")
        await self.ctx.artifact("spec", spec.model_dump())
        return spec

    async def _design_tests(self, spec: ProblemSpec) -> TestPlan:
        async with self.ctx.stage("design_tests", "Test Designer: edge cases + brute-force oracle") as st:
            plan, u = await agents.design_tests(self.ctx.llm, spec)
            st.usage(u)
            st.note(f"{len(plan.cases)} targeted inputs, brute-force reference, random input "
                    f"generator{', custom answer checker' if plan.checker_code.strip() else ''}")
        await self.ctx.artifact("test_plan", plan.model_dump())
        return plan

    async def _solve(self, spec: ProblemSpec) -> Solution:
        async with self.ctx.stage("solve", "Solver: design the algorithm") as st:
            solution, u = await agents.solve(self.ctx.llm, spec)
            st.usage(u)
            st.note(f"{solution.approach} · claims {solution.time_complexity} time")
        return solution
