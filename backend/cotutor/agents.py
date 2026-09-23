"""The specialist agents. Each is one focused LLM call with a narrow contract.

Agents only *propose* (specs, tests, code, fixes); nothing they claim is trusted until the
pipeline has executed it. Prompts therefore ask for executable artifacts rather than
assertions: a brute-force reference instead of hand-computed expected outputs, a checker
instead of "any order is fine", an input generator instead of "it's O(n)".
"""

from __future__ import annotations

import json

from .llm import LLMClient, Usage
from .schemas import DebugResult, Explanation, LessonDeep, LessonIntro, ProblemSpec, Solution, TestPlan

PYTHON_ENV_NOTE = (
    "Code runs on CPython 3.12 with only the standard library. `List`, `Optional`, "
    "`collections`, `heapq`, `bisect`, `math`, `functools`, `itertools` and LeetCode's "
    "`ListNode(val, next)` / `TreeNode(val, left, right)` are pre-imported. ListNode/TreeNode "
    "arguments are passed as real nodes; in JSON they are written as lists (trees in "
    "LeetCode level order with null)."
)


def _spec_block(spec: ProblemSpec) -> str:
    params = ", ".join(f"{p.name}: {p.type}" for p in spec.params)
    examples = "\n".join(f"  args={e.args_json} -> {e.expected_json}" for e in spec.examples)
    return (
        f"Title: {spec.title}\nTask: {spec.summary}\n"
        f"Signature: def {spec.entry}({params}) -> {spec.return_type}\n"
        f"Constraints: {'; '.join(spec.constraints) or 'none given'}\n"
        f"Examples:\n{examples}"
    )


async def analyze(llm: LLMClient, problem: str) -> tuple[ProblemSpec, Usage]:
    system = (
        "You are the Analyst in an algorithm-tutoring system. Turn a user's problem statement "
        "(often informal or copied from LeetCode) into a precise, machine-checkable spec. "
        "Use LeetCode's conventional function name and argument order when the problem is a "
        "known one. Every example's expected output must be exactly right: prefer small "
        "examples you can verify by hand. " + PYTHON_ENV_NOTE
    )
    return await llm.structured(
        agent="analyst", system=system, prompt=f"Problem statement:\n{problem}",
        schema=ProblemSpec, tier="fast", temperature=0.1,
    )


async def design_tests(
    llm: LLMClient, spec: ProblemSpec, feedback: str | None = None
) -> tuple[TestPlan, Usage]:
    system = (
        "You are the Test Designer. Your job is to catch wrong solutions. Produce:\n"
        "1. Inputs only (no expected outputs) for edge cases and tricky cases: empty/minimal "
        "inputs, duplicates, negatives, boundaries from the constraints, off-by-one traps. "
        "Keep each input small (under 30 elements) except at most one 'large' case.\n"
        "2. A NAIVE brute-force reference solution that is obviously correct: enumerate every "
        "candidate (all pairs, all substrings, all subsets, every start index...) and check "
        "each one directly. Do NOT use the clever technique the problem is known for (no "
        "sliding window, two pointers, hash-map shortcuts, memoization or greedy tricks) "
        "unless no simpler correct approach exists. Expected outputs are computed by running "
        "it, and students study it as the starting point before learning the optimization, "
        "so use clear names and the simplest possible structure.\n"
        "3. generate(rng, n) returning a list of args for a random valid input of size n "
        "(use only rng = random.Random), and generate_worst(rng, n) producing the input that "
        "maximizes running time for a typical efficient solution, so timing reveals growth. "
        "n is the main size variable of the problem.\n"
        "4. If the problem accepts more than one correct output, check(args, got, expected) "
        "that validates `got` directly against the problem rules (do not just compare to "
        "`expected`). Otherwise return an empty string.\n" + PYTHON_ENV_NOTE
    )
    prompt = _spec_block(spec)
    if feedback:
        prompt += f"\n\nFeedback on your previous attempt:\n{feedback}"
    return await llm.structured(
        agent="test_designer", system=system, prompt=prompt,
        schema=TestPlan, tier="smart", temperature=0.3,
    )


async def solve(llm: LLMClient, spec: ProblemSpec) -> tuple[Solution, Usage]:
    system = (
        "You are the Solver, an expert competitive programmer and patient teacher. Find the "
        "optimal approach, explain it as ordered reasoning steps a student can follow, then "
        "write clean, idiomatic Python with meaningful variable names (they are shown in an "
        "animated visualization). Avoid printing. " + PYTHON_ENV_NOTE
    )
    return await llm.structured(
        agent="solver", system=system, prompt=_spec_block(spec),
        schema=Solution, tier="smart", temperature=0.2,
    )


async def debug(
    llm: LLMClient, spec: ProblemSpec, solution: Solution, failures: list[dict], history: list[str]
) -> tuple[DebugResult, Usage]:
    system = (
        "You are the Debugger. A solution failed verification. Find the root cause from the "
        "concrete failing cases and return a corrected full solution. Change only what is "
        "needed. Expected outputs from the problem's own examples are authoritative; "
        "expected outputs marked 'reference' come from a brute-force oracle and are almost "
        "always right. Only set blame='test' if you can prove the expected value violates "
        "the problem statement. " + PYTHON_ENV_NOTE
    )
    prompt = (
        f"{_spec_block(spec)}\n\nCurrent code:\n```python\n{solution.code}\n```\n\n"
        f"Failing cases:\n{json.dumps(failures, indent=1)[:6000]}"
    )
    if history:
        prompt += "\n\nPrevious fix attempts that did NOT work:\n- " + "\n- ".join(history)
    return await llm.structured(
        agent="debugger", system=system, prompt=prompt, schema=DebugResult,
        tier="smart", temperature=0.2,
    )


async def explain(
    llm: LLMClient, spec: ProblemSpec, solution: Solution
) -> tuple[Explanation, Usage]:
    system = (
        "You are the Tutor. Explain a verified solution to a student visually. The flowchart "
        "must mirror the code's real control flow: use 'loop' nodes for loops with an edge "
        "back from the loop body, 'decision' nodes for branches with labeled yes/no edges, "
        "5-10 nodes total, ids like n1, n2. For the animation, list the variables that tell "
        "the story (the data structure being built, the pointers/indices, the answer) using "
        "their exact names in the code, and pick a small input (4-8 elements) where "
        "something interesting happens. Do not change the algorithm."
    )
    prompt = (
        f"{_spec_block(spec)}\n\nApproach: {solution.approach}\nKey insight: "
        f"{solution.key_insight}\nCode:\n```python\n{solution.code}\n```"
    )
    return await llm.structured(
        agent="tutor", system=system, prompt=prompt, schema=Explanation,
        tier="fast", temperature=0.4,
    )


def numbered(code: str) -> str:
    return "\n".join(f"{i:>3} | {line}" for i, line in enumerate(code.rstrip().split("\n"), 1))


COACH_STYLE = (
    "You are the Coach in an algorithm-tutoring app. The goal is that the student learns the "
    "reusable reasoning (how to recognize the pattern and derive the solution), not that they "
    "memorize this answer. Write for a student who knows basic Python but is new to the "
    "pattern: concrete, plain language, no fluff, no praise."
)


async def coach_intro(
    llm: LLMClient, problem: str, spec: ProblemSpec, solution: Solution, brute_force: str,
    brute_is_optimal: bool = False,
) -> tuple[LessonIntro, Usage]:
    system = COACH_STYLE + (
        " Build the first half of the lesson: which pattern applies and what in the wording "
        "gives it away, then the brute force and where its wasted work is. Pattern options "
        "must be plausible for this problem (common confusions), exactly one correct. Signal "
        "phrases must be copied verbatim from the original statement. Hints must lead toward "
        "the bottleneck without naming it."
    )
    prompt = (
        f"Original problem statement:\n{problem}\n\n{_spec_block(spec)}\n\n"
        f"Optimal approach (for your reference, do not reveal in hints): {solution.approach}. "
        f"{solution.key_insight}\n\nBrute-force code (line-numbered):\n{numbered(brute_force)}"
    )
    if brute_is_optimal:
        prompt += (
            "\n\nMeasured: the straightforward approach above already grows as slowly as the "
            "optimal one, so there is no wasted work to remove. Say so honestly: set "
            "bottleneck_line to 0, use `bottleneck` to explain why the direct approach is "
            "already optimal, and make the hints about why no faster approach is possible."
        )
    return await llm.structured(
        agent="coach_intro", system=system, prompt=prompt, schema=LessonIntro,
        tier="smart", temperature=0.3,
    )


async def coach_deep(
    llm: LLMClient, spec: ProblemSpec, solution: Solution, brute_force: str,
    evidence: str, bugs: list[str],
) -> tuple[LessonDeep, Usage]:
    system = COACH_STYLE + (
        " Build the second half of the lesson: how the optimized solution removes the "
        "bottleneck, and WHY its complexity is what it is, derived line by line from the code. "
        "Ground the derivation in the measured evidence provided (exact step counts per line "
        "on growing inputs); if the evidence contradicts the claimed complexity, trust the "
        "evidence and say so."
    )
    prompt = (
        f"{_spec_block(spec)}\n\nBrute force:\n{numbered(brute_force)}\n\n"
        f"Optimized solution ({solution.approach}, claimed {solution.time_complexity} time, "
        f"{solution.space_complexity} space):\n{numbered(solution.code)}\n\n"
        f"Measured evidence:\n{evidence}"
    )
    if bugs:
        prompt += "\n\nBugs found while verifying earlier drafts:\n- " + "\n- ".join(bugs)
    return await llm.structured(
        agent="coach_deep", system=system, prompt=prompt, schema=LessonDeep,
        tier="smart", temperature=0.3,
    )
