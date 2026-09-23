"""Teaching: the Coach's lesson, the Tutor's visual explanation and the execution trace.

Teaching steps are best-effort: if one fails, the run continues and the UI shows that part
as unavailable, because a verified solution is still useful without narration.
"""

from __future__ import annotations

from typing import Any

from .. import agents
from ..llm import LLMError
from ..schemas import Explanation, ProblemSpec, Solution, TestPlan
from .context import RunContext, harness_spec, parse_args


def _line_count(code: str) -> int:
    return len(code.rstrip().split("\n"))


class Teacher:
    def __init__(self, ctx: RunContext):
        self.ctx = ctx

    async def lesson_intro(self, problem: str, spec: ProblemSpec, solution: Solution, plan: TestPlan,
                           brute_is_optimal: bool) -> dict[str, Any] | None:
        """Pattern quiz, signal phrases, brute force and its bottleneck."""
        try:
            async with self.ctx.stage("coach_intro", "Coach: pattern, brute force and its bottleneck") as st:
                intro, u = await agents.coach_intro(self.ctx.llm, problem, spec, solution,
                                                    plan.reference_solution, brute_is_optimal)
                st.usage(u)
                st.note(f"Pattern: {intro.pattern} · {len(intro.bottleneck_hints)} hints")
        except LLMError:
            return None
        data = intro.model_dump()
        if brute_is_optimal or not 1 <= data["bottleneck_line"] <= _line_count(plan.reference_solution):
            data["bottleneck_line"] = None
        if sum(o["correct"] for o in data["pattern_options"]) != 1:
            # Keep the quiz gradeable: the named pattern is the answer.
            for o in data["pattern_options"]:
                o["correct"] = o["name"].strip().lower() == intro.pattern.strip().lower()
            if not any(o["correct"] for o in data["pattern_options"]):
                data["pattern_options"].append({"name": intro.pattern, "correct": True,
                                                "feedback": intro.pattern_summary})
        data |= {"brute_force_code": plan.reference_solution, "brute_is_optimal": brute_is_optimal}
        await self.ctx.artifact("lesson_intro", data)
        return data

    async def lesson_deep(self, spec: ProblemSpec, plan: TestPlan, solution: Solution,
                          complexity: dict[str, Any] | None, counts: dict[str, Any] | None,
                          bugs: list[str]) -> dict[str, Any] | None:
        """The insight and a line-by-line complexity derivation grounded in measured counts."""
        try:
            async with self.ctx.stage("coach_deep", "Coach: why the complexity is what it is") as st:
                deep, u = await agents.coach_deep(self.ctx.llm, spec, solution, plan.reference_solution,
                                                  self._evidence(complexity, counts), bugs)
                st.usage(u)
                st.note(f"{len(deep.derivation)} line-level costs · takeaway ready")
        except LLMError:
            return None
        data = deep.model_dump()
        n_lines = _line_count(solution.code)
        data["derivation"] = [d for d in data["derivation"] if 1 <= d["line"] <= n_lines]
        data["code"] = solution.code
        await self.ctx.artifact("lesson_deep", data)
        return data

    @staticmethod
    def _evidence(complexity: dict[str, Any] | None, counts: dict[str, Any] | None) -> str:
        lines = []
        for name in ("solution", "brute_force"):
            for run in (counts or {}).get(name, []):
                per_line = ", ".join(f"line {k}: {v}" for k, v in run["counts"].items())
                lines.append(f"{name} n={run['n']}: {run['total']} steps ({per_line})")
        if complexity and complexity.get("slope") is not None:
            lines.append(f"Wall-clock growth on large inputs: n^{complexity['slope']:.2f} "
                         f"({complexity['verdict'].replace('_', ' ')})")
        return "\n".join(lines) or "none"

    async def explanation(self, spec: ProblemSpec, solution: Solution) -> Explanation | None:
        try:
            async with self.ctx.stage("explain", "Tutor: build the visual explanation") as st:
                explanation, u = await agents.explain(self.ctx.llm, spec, solution)
                st.usage(u)
                st.note(f"{len(explanation.flow_nodes)}-node flowchart, "
                        f"{len(explanation.viz_vars)} variables to animate")
        except LLMError:
            return None
        await self.ctx.artifact("explanation", explanation.model_dump())
        return explanation

    async def trace(self, spec: ProblemSpec, solution: Solution,
                    explanation: Explanation | None) -> dict[str, Any] | None:
        """Record line-by-line execution on the Tutor's illustrative input (or an example)."""
        args = parse_args(explanation.viz_args_json) if explanation else None
        if args is None:
            args = next((a for e in spec.examples if (a := parse_args(e.args_json)) is not None), None)
        if args is None:
            return None
        async with self.ctx.stage("trace", "Tracer: record execution for animation") as st:
            res = await self.ctx.execute({"kind": "trace", "spec": harness_spec(spec),
                                          "code": solution.code, "args": args, "max_steps": 600})
            if not res.get("ok"):
                st.note("Tracing failed.", "warning")
                return None
            st.note(f"{len(res['steps'])} execution steps recorded"
                    + (" (truncated)" if res.get("truncated") else ""))
        await self.ctx.artifact("trace", res | {"args": args, "code": solution.code})
        return res
