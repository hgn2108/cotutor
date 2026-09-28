"""Verification: build the test suite, validate the oracle, then verify ⟲ debug."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .. import agents
from ..runtime.harness import outputs_match
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
                              "source": "example", "label": f"Example {i}",
                              "from_statement": ex.from_statement})
        for i, draft in enumerate(plan.cases, 1):
            args = parse_args(draft.args_json)
            if args is not None:
                cases.append({"id": f"t{i}", "args": args, "source": "reference",
                              "label": draft.name, "category": draft.category,
                              "rationale": draft.rationale})
        return cases

    async def validate_oracle(self, spec: ProblemSpec, plan: TestPlan,
                              cases: list[dict[str, Any]], solution: Solution) -> Oracle:
        """Verify the verifier: the oracle must reproduce the problem's own examples.

        Examples copied from the user's statement are authoritative. Examples the Analyst made up
        (statements without examples) can be wrong: if the brute force and the solution, written
        independently, agree with each other against a made-up example, the example is corrected
        instead of "fixing" correct code to match it.
        """
        oracle = Oracle(plan.reference_solution, plan.checker_code.strip() or None)
        corrected: list[str] = []
        async with self.ctx.stage("oracle", "Check the answer key: reference solution vs. examples") as st:
            examples = [c for c in cases if c["source"] == "example"]
            if not examples:
                st.note("No parseable examples; generated cases can only catch crashes.", "warning")
            else:
                res = await self.ctx.execute({
                    "kind": "tests", "spec": harness_spec(spec), "code": oracle.reference_code,
                    "checker_code": oracle.checker_code, "cases": _for_harness(examples),
                })
                failed = [c for c in res.get("cases", []) if c["status"] != "pass"] if res.get("ok") else None
                # An example whose input can't be built was written down wrong; drop it.
                broken = {c["id"] for c in failed or [] if c["status"] == "invalid"}
                if broken:
                    cases[:] = [c for c in cases if c["id"] not in broken]
                    examples = [c for c in examples if c["id"] not in broken]
                    failed = [c for c in failed if c["id"] not in broken]
                    st.note(f"Dropped {len(broken)} example(s) with malformed input.", "warning")
                if failed:
                    corrected = await self._correct_invented(spec, solution, examples, failed)
                oracle.trusted = failed is not None and (not failed or len(corrected) == len(failed))
                if oracle.trusted and corrected:
                    st.note(f"Corrected {len(corrected)} made-up example(s): the brute force and the "
                            "solution independently agreed on a different answer.", "warning")
                elif oracle.trusted:
                    st.note(f"The reference solution reproduces all {len(examples)} examples, "
                            "so it can grade the other tests.")
                else:
                    st.note("The reference solution got an example wrong, so only the examples "
                            "are graded exactly.", "warning")
        await self.ctx.artifact("oracle", {"trusted": oracle.trusted, "corrected_examples": corrected,
                                           "has_checker": bool(oracle.checker_code)})
        return oracle

    async def _correct_invented(self, spec: ProblemSpec, solution: Solution,
                                examples: list[dict[str, Any]], failed: list[dict]) -> list[str]:
        by_id = {c["id"]: c for c in examples}
        if any(by_id[f["id"]].get("from_statement", True) or f["status"] != "fail" for f in failed):
            return []  # a statement example disagrees: the oracle is wrong, not the example
        res = await self.ctx.execute({
            "kind": "tests", "spec": harness_spec(spec), "code": solution.code,
            "cases": [{"id": f["id"], "args": by_id[f["id"]]["args"]} for f in failed],
        })
        sol_out = {c["id"]: c.get("got") for c in res.get("cases", [])} if res.get("ok") else {}
        agreed = [f for f in failed
                  if f["id"] in sol_out and outputs_match(sol_out[f["id"]], f["got"], spec.comparison)]
        if len(agreed) != len(failed):
            return []
        for f in agreed:
            by_id[f["id"]].update(expected=f["got"], label=by_id[f["id"]]["label"] + " (corrected)")
        return [f["id"] for f in agreed]

    async def verify_and_debug(self, spec: ProblemSpec, plan: TestPlan, solution: Solution,
                               cases: list[dict[str, Any]], oracle: Oracle) -> VerificationResult:
        by_id = {c["id"]: c for c in cases}
        history: list[str] = []
        bugs: list[str] = []
        verified, trials, passed, attempt, refereed, recheck = False, 0, 0, 0, False, False
        while True:
            verified, failures, passed, trials = await self._verify_once(
                spec, plan, solution, by_id, oracle, attempt, recheck)
            if verified or attempt == self.ctx.config.max_debug_attempts:
                break
            # The reference is agent-written too. Before "fixing" code to match it, let an
            # independent referee check the first disagreement against the statement.
            dispute = self._dispute(failures, by_id) if oracle.trusted and not refereed else None
            if dispute is not None:
                refereed = True
                if await self._referee(spec, dispute, by_id):
                    oracle.trusted = False
                    recheck = True
                    continue  # re-verify the same code without the reference
            attempt += 1
            recheck = False
            solution = await self._debug_once(spec, solution, failures, by_id, history, bugs, attempt)
        return VerificationResult(solution, verified, attempt + 1, passed, len(by_id), trials, bugs)

    @staticmethod
    def _dispute(failures: list[dict], by_id: dict[str, dict]) -> dict | None:
        """The smallest wrong-answer failure, if every failure is on a reference-graded input."""
        if not failures or any(by_id.get(f["id"], {}).get("source") not in ("reference", "stress")
                               or f.get("status") != "fail" or "got" not in f for f in failures):
            return None
        return min(failures, key=lambda f: len(json.dumps(by_id[f["id"]]["args"])))

    async def _referee(self, spec: ProblemSpec, failure: dict, by_id: dict[str, dict]) -> bool:
        """True when the referee sides with the solution against the reference."""
        args = by_id[failure["id"]]["args"]
        async with self.ctx.stage("referee", "Referee: settle a disagreement") as st:
            winner, reasoning, u = await agents.referee(
                self.ctx.llm, spec, self.ctx.statement, args, failure.get("expected"), failure.get("got"))
            st.usage(u)
            if winner == "solution":
                st.note("Sided with the solution: the reference solution misreads the problem, so "
                        "it no longer grades tests. " + reasoning[:200], "warning")
            else:
                st.note(f"Sided with the {'reference solution' if winner == 'reference' else 'neither'}; "
                        "debugging the solution. " + reasoning[:200])
        await self.ctx.artifact("referee", {"case": failure["id"], "winner": winner, "reasoning": reasoning})
        return winner == "solution"

    async def _verify_once(self, spec, plan, solution, by_id, oracle: Oracle, attempt: int,
                           recheck: bool = False):
        hspec = harness_spec(spec)
        label = "Verifier: run tests" if attempt == 0 else f"Verifier: re-test fix #{attempt}"
        if recheck:
            label = "Verifier: re-test without the reference solution"
        trials, counterexample = 0, None
        async with self.ctx.stage(f"verify_{attempt}" + ("_recheck" if recheck else ""), label) as st:
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
            invalid = [r["id"] for r in results if r["status"] == "invalid"]
            for cid in invalid:
                by_id.pop(cid, None)  # broken tests don't count for or against the solution
            results_total = len(results) - len(invalid)

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
                                  "source": "stress", "label": "Found by random testing"}
                    failures = [{"id": cid, "status": "fail" if "got" in counterexample else "error",
                                 **counterexample}]

            verified = not failures
            if counterexample:
                note = (f"{passed}/{results_total} tests pass, but random testing found a "
                        f"failing input after {trials} tries")
            else:
                note = f"{passed}/{results_total} tests pass" + (
                    f", {trials} random inputs agree with the reference solution" if trials else "")
                if failures:
                    note += f" ({len(failures)} failing)"
            if invalid:
                note += f"; skipped {len(invalid)} malformed input(s)"
            st.note(note, "done" if verified else "failed")
        await self.ctx.artifact("verification", {
            "attempt": attempt, "recheck": recheck, "verified": verified, "results": results,
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
