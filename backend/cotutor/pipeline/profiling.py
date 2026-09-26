"""Profiling: exact step counts per line, growth at scale, and the naive-brute-force check.

LLM-written "worst case" generators are not always worst, so every measurement runs with both
the random and the worst-case generator and keeps whichever grows faster.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import agents
from ..complexity import check as check_complexity
from ..complexity import expected_slope, normalize_claim
from ..llm import LLMError
from ..runtime.harness import fit_slope
from ..schemas import ProblemSpec, Solution, TestPlan
from .context import RunContext, harness_spec

GENERATORS = ("worst", "random")
LESSON_SIZES = [4, 8, 16, 32]  # small enough to read, large enough to show growth
RANDOM_TRIALS = 5              # random inputs are averaged; one sample is too noisy at small n


@dataclass
class ReferenceCheck:
    plan: TestPlan
    brute_is_optimal: bool  # no slower straightforward approach exists


class Profiler:
    def __init__(self, ctx: RunContext):
        self.ctx = ctx

    async def _line_counts(self, spec: ProblemSpec, code: str, generator: str, which: str,
                           sizes: list[int]) -> dict[str, Any] | None:
        res = await self.ctx.execute({
            "kind": "line_counts", "spec": harness_spec(spec), "code": code,
            "generator_code": generator, "sizes": sizes, "which": which,
            "trials": RANDOM_TRIALS if which == "random" else 1,
        })
        return res if res.get("ok") and res.get("runs") else None

    async def step_growth(self, spec: ProblemSpec, code: str, generator: str) -> float | None:
        """Growth exponent fitted to exact step counts, worst of both generators."""
        best = None
        for which in GENERATORS:
            res = await self._line_counts(spec, code, generator, which, [8, 16, 32, 64])
            runs = [r for r in (res or {}).get("runs", []) if not r["capped"] and r["total"] > 0]
            g = fit_slope([[r["n"], r["total"]] for r in runs])
            if g is not None:
                best = g if best is None else max(best, g)
        return best

    async def ensure_naive_reference(self, spec: ProblemSpec, plan: TestPlan,
                                     solution: Solution) -> ReferenceCheck:
        """The brute force doubles as the lesson's starting point, so it must actually be naive.

        If the reference grows no faster than the solution, the Test Designer gets one retry
        with that feedback. If it still doesn't, the problem has no slower obvious approach
        and the lesson says so instead of inventing a bottleneck.
        """
        if not plan.generator_code.strip():
            return ReferenceCheck(plan, False)
        async with self.ctx.stage("naive_check", "Check the brute force is really brute force") as st:
            sol = await self.step_growth(spec, solution.code, plan.generator_code)
            ref = await self.step_growth(spec, plan.reference_solution, plan.generator_code)
            if sol is None or ref is None or ref >= sol + 0.5:
                st.note("Brute force grows faster than the solution, as a starting point should."
                        if sol is not None and ref is not None else "Could not measure; skipped.")
                return ReferenceCheck(plan, False)
            st.note(f"Reference grows like n^{ref:.1f}, same as the solution. Asking for a naive one.",
                    "warning")
            feedback = (
                f"Your reference solution is not naive: measured step counts grow like n^{ref:.1f}, "
                f"the same as the optimized solution ({solution.approach}). Write a brute force that "
                "enumerates candidates directly, without that technique, and make sure the generators' "
                "n scales the input dimension that dominates its running time."
            )
            try:
                retry, u = await agents.design_tests(self.ctx.llm, spec, feedback)
                st.usage(u)
                ref2 = await self.step_growth(spec, retry.reference_solution,
                                              retry.generator_code or plan.generator_code)
            except LLMError:
                retry, ref2 = None, None
            if retry is not None and ref2 is not None and ref2 >= sol + 0.5:
                st.note(f"Rewrote the brute force: it now grows like n^{ref2:.1f} vs n^{sol:.1f}.")
                await self.ctx.artifact("test_plan", retry.model_dump())
                return ReferenceCheck(retry, False)
            if not self._claims_equivalent(plan, solution):
                # The counts can't tell them apart, but the claimed complexities differ: the
                # generator's n likely doesn't grow the dimension that matters (e.g. the largest
                # pile in Koko Eating Bananas). Telling learners "the direct approach is optimal"
                # needs both the measurement and the claims to agree.
                st.note(f"Inconclusive: the brute force claims {plan.reference_time_complexity} vs "
                        f"{solution.time_complexity}, but measured growth matches; the input "
                        "generator likely doesn't scale the dominant dimension.", "warning")
                return ReferenceCheck(plan, False)
            st.note("No slower straightforward approach exists; the direct approach is already optimal.")
            return ReferenceCheck(plan, True)

    @staticmethod
    def _claims_equivalent(plan: TestPlan, solution: Solution) -> bool:
        """Do the brute force and the solution claim the same complexity?"""
        ref, sol = plan.reference_time_complexity, solution.time_complexity
        ref_slope, sol_slope = expected_slope(ref), expected_slope(sol)
        if ref_slope is not None and sol_slope is not None:
            return abs(ref_slope - sol_slope) <= 0.4
        return normalize_claim(ref) == normalize_claim(sol)  # e.g. both "O(m * n)"

    async def growth_at_scale(self, spec: ProblemSpec, plan: TestPlan,
                              solution: Solution) -> dict[str, Any] | None:
        """Wall-clock timing on doubling inputs, compared with the claimed Big-O."""
        if not plan.generator_code.strip():
            return None
        async with self.ctx.stage("complexity", "Profiler: measure growth rate") as st:
            res: dict[str, Any] = {}
            for which in GENERATORS:
                r = await self.ctx.execute({"kind": "complexity", "spec": harness_spec(spec),
                                            "code": solution.code, "generator_code": plan.generator_code,
                                            "which": which})
                if r.get("ok") and (not res or (r.get("slope") or -1) > (res.get("slope") or -1)):
                    res = r
            if not res.get("ok"):
                st.note("Could not time the solution on generated inputs.", "warning")
                return None
            slope = res.get("slope")
            if res.get("stopped") and len(res.get("points", [])) < 4:
                slope = None  # too few trustworthy points to judge growth
            chk = check_complexity(solution.time_complexity, slope)
            if res.get("stopped"):
                chk.note += f" (Sweep {res['stopped']}.)"
            st.note(chk.note, "done" if chk.verdict in ("consistent", "inconclusive") else "warning")
            data = {"points": res["points"], "slope": slope, "claimed": chk.claimed,
                    "expected_slope": chk.expected_slope, "verdict": chk.verdict, "note": chk.note,
                    "used_worst_case": res.get("used_worst_case", False)}
        await self.ctx.artifact("complexity", data)
        return data

    async def lesson_step_counts(self, spec: ProblemSpec, plan: TestPlan,
                                 solution: Solution) -> dict[str, Any] | None:
        """Per-line step counts for the lesson: the solution on its hardest input, and the
        brute force on the same kind of input so the two are comparable."""
        if not plan.generator_code.strip():
            return None
        async with self.ctx.stage("line_counts", "Profiler: count how often each line runs") as st:
            candidates = [r for w in GENERATORS
                          if (r := await self._line_counts(spec, solution.code, plan.generator_code,
                                                           w, LESSON_SIZES))]
            if not candidates:
                st.note("Could not count steps.", "warning")
                return None
            chosen = max(candidates, key=lambda r: r["runs"][-1]["total"])
            which = "worst" if chosen.get("used_worst_case") else "random"
            out: dict[str, Any] = {"solution": chosen["runs"],
                                   "used_worst_case": chosen.get("used_worst_case", False)}
            brute = await self._line_counts(spec, plan.reference_solution, plan.generator_code,
                                            which, LESSON_SIZES)
            if brute:
                out["brute_force"] = brute["runs"]

            def totals(runs):
                return " → ".join(str(r["total"]) for r in runs)

            st.note(f"n = {', '.join(str(r['n']) for r in out['solution'])}: "
                    f"{totals(out['solution'])} steps"
                    + (f" (brute force: {totals(out['brute_force'])})" if "brute_force" in out else ""))
        await self.ctx.artifact("line_counts", out)
        return out
