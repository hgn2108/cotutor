"""Verification: build the test suite, validate the oracle, then verify ⟲ debug."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .. import agents
from ..schemas import ProblemSpec, Solution, TestPlan
from .context import RunContext, harness_spec, parse_args

FAILING = {"fail", "error", "timeout"}


@dataclass
class Oracle:
    """The brute-force reference and optional checker, trusted only if they pass the examples."""

    reference_code: str
    checker_code: str | None
    trusted: bool = False


@dataclass
class VerificationResult:
    solution: Solution
    verified: bool
    attempts: int
    passed: int
    total: int
    stress_trials: int
    bugs: list[str] = field(default_factory=list)  # debugger diagnoses, used to teach mistakes


def _for_harness(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only send the harness what it needs."""
    keep = ("id", "args", "expected")
    return [{k: c[k] for k in keep if k in c} for c in cases]


class Verifier:
    def __init__(self, ctx: RunContext):
        self.ctx = ctx

    @staticmethod
    def build_cases(spec: ProblemSpec, plan: TestPlan) -> list[dict[str, Any]]:
        """Problem examples (with expected outputs) plus the Test Designer's inputs.

        Malformed agent output is dropped rather than trusted.
        """
        cases: list[dict[str, Any]] = []
        for i, ex in enumerate(spec.examples, 1):
            args = parse_args(ex.args_json)
            try:
                expected = json.loads(ex.expected_json)
            except json.JSONDecodeError:
                continue
            if args is not None:
                cases.append({"id": f"ex{i}", "args": args, "expected": expected,
                              "source": "example", "label": f"Example {i}"})
        for i, draft in enumerate(plan.cases, 1):
            args = parse_args(draft.args_json)
            if args is not None:
                cases.append({"id": f"t{i}", "args": args, "source": "reference",
                              "label": draft.name, "category": draft.category,
                              "rationale": draft.rationale})
        return cases

    async def validate_oracle(self, spec: ProblemSpec, plan: TestPlan,
                              cases: list[dict[str, Any]]) -> Oracle:
        """Verify the verifier: the oracle must reproduce the problem's own examples."""
        oracle = Oracle(plan.reference_solution, plan.checker_code.strip() or None)
        async with self.ctx.stage("oracle", "Verify the verifier: check oracle on examples") as st:
            examples = [c for c in cases if c["source"] == "example"]
            if not examples:
                st.note("No parseable examples; generated cases can only catch crashes.", "warning")
            else:
                res = await self.ctx.execute({
                    "kind": "tests", "spec": harness_spec(spec), "code": oracle.reference_code,
                    "checker_code": oracle.checker_code, "cases": _for_harness(examples),
                })
                oracle.trusted = bool(res.get("ok") and all(c["status"] == "pass" for c in res["cases"]))
                if oracle.trusted:
                    st.note(f"Brute-force oracle matches all {len(examples)} examples; "
                            "using it to compute expected outputs.")
                else:
                    st.note("Oracle disagreed with the examples, so only the examples are "
                            "checked for correctness.", "warning")
        await self.ctx.artifact("oracle", {"trusted": oracle.trusted,
                                           "has_checker": bool(oracle.checker_code)})
        return oracle

    async def verify_and_debug(self, spec: ProblemSpec, plan: TestPlan, solution: Solution,
                               cases: list[dict[str, Any]], oracle: Oracle) -> VerificationResult:
        by_id = {c["id"]: c for c in cases}
        history: list[str] = []
        bugs: list[str] = []
        verified, trials, passed, attempt = False, 0, 0, 0
        for attempt in range(self.ctx.config.max_debug_attempts + 1):
            verified, failures, passed, trials = await self._verify_once(
                spec, plan, solution, by_id, oracle, attempt)
            if verified or attempt == self.ctx.config.max_debug_attempts:
                break
            solution = await self._debug_once(spec, solution, failures, by_id, history, bugs, attempt + 1)
        return VerificationResult(solution, verified, attempt + 1, passed, len(by_id), trials, bugs)

    async def _verify_once(self, spec, plan, solution, by_id, oracle: Oracle, attempt: int):
        hspec = harness_spec(spec)
        label = "Verifier: run tests" if attempt == 0 else f"Verifier: re-test fix #{attempt}"
        trials, counterexample = 0, None
        async with self.ctx.stage(f"verify_{attempt}", label) as st:
            job = {"kind": "tests", "spec": hspec, "code": solution.code,
                   "cases": _for_harness(list(by_id.values()))}
            if oracle.trusted:
                job |= {"reference_code": oracle.reference_code, "checker_code": oracle.checker_code}
            res = await self.ctx.execute(job)
            results = res.get("cases", []) if res.get("ok") else []
            failures = [r for r in results if r["status"] in FAILING]
            if not res.get("ok"):
                failures = [{"id": "load", "status": "error", "error": res.get("error")}]
            passed = sum(r["status"] in ("pass", "ran") for r in results)

            if not failures and oracle.trusted and plan.generator_code.strip():
                diff = await self.ctx.execute({
                    "kind": "differential", "spec": hspec, "code": solution.code,
                    "reference_code": oracle.reference_code, "checker_code": oracle.checker_code,
                    "generator_code": plan.generator_code,
                    "trials": self.ctx.config.differential_trials, "seed": attempt,
                })
                trials = diff.get("trials", 0) if diff.get("ok") else 0
                counterexample = diff.get("counterexample") if diff.get("ok") else None
                if counterexample:
                    cid = f"stress{attempt + 1}"
                    # Keep it as a regression test for every later attempt.
                    by_id[cid] = {"id": cid, "args": counterexample["args"],
                                  "source": "stress", "label": "Found by random stress test"}
                    failures = [{"id": cid, "status": "fail" if "got" in counterexample else "error",
                                 **counterexample}]

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
        await self.ctx.artifact("verification", {
            "attempt": attempt, "verified": verified, "results": results,
            "cases": list(by_id.values()), "stress_trials": trials,
            "counterexample": counterexample, "load_error": None if res.get("ok") else res.get("error"),
        })
        return verified, failures, passed, trials

    async def _debug_once(self, spec, solution: Solution, failures, by_id, history: list[str],
                          bugs: list[str], n: int) -> Solution:
        async with self.ctx.stage(f"debug_{n}", f"Debugger: fix attempt #{n}") as st:
            detailed = [{**by_id.get(f["id"], {}), **f} for f in failures[:4]]
            for d in detailed:
                d.pop("rationale", None)
            fix, u = await agents.debug(self.ctx.llm, spec, solution, detailed, history)
            st.usage(u)
            # Only oracle-generated cases may be disputed; the problem's examples are authoritative.
            disputable = [f["id"] for f in failures
                          if by_id.get(f["id"], {}).get("source") in ("reference", "stress")]
            if fix.blame == "test" and disputable:
                for cid in disputable:
                    by_id.pop(cid, None)
                st.note(f"Disputed {len(disputable)} oracle-generated test(s): {fix.diagnosis}")
                return solution
            st.note(fix.diagnosis)
        before, solution = solution.code, solution.model_copy(update={"code": fix.code})
        history.append(fix.fix_summary)
        bugs.append(fix.diagnosis)
        await self.ctx.artifact("debug_attempt", {
            "attempt": n, "diagnosis": fix.diagnosis, "fix_summary": fix.fix_summary,
            "before": before, "after": fix.code, "failures": detailed,
        })
        await self.ctx.artifact("solution", solution.model_dump() | {"revision": n})
        return solution
