"""Test Designer: edge cases, a naive brute-force oracle, input generators and an optional checker."""

from __future__ import annotations

from ..llm import LLMClient, Usage
from ..schemas import ProblemSpec, TestPlan
from .common import PYTHON_ENV_NOTE, spec_block


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
        "n must scale the part of the input that dominates running time (e.g. the target amount in "
        "coin change, the string length for substrings, the node count for trees), because growth "
        "is measured against n. Never cap or clamp n: the profiler calls "
        "these with n up to 1,000,000, and inputs must keep growing with n.\n"
        "4. If the problem accepts more than one correct output, check(args, got, expected) "
        "that validates `got` directly against the problem rules (do not just compare to "
        "`expected`). Otherwise return an empty string.\n" + PYTHON_ENV_NOTE
    )
    prompt = spec_block(spec)
    if feedback:
        prompt += f"\n\nFeedback on your previous attempt:\n{feedback}"
    return await llm.structured(
        agent="test_designer", system=system, prompt=prompt,
        schema=TestPlan, tier="smart", temperature=0.3,
    )
