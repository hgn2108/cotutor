"""Solver: the optimal approach, as reasoning steps plus code."""

from __future__ import annotations

from ..llm import LLMClient, Usage
from ..schemas import ProblemSpec, Solution
from .common import PYTHON_ENV_NOTE, spec_block


async def solve(llm: LLMClient, spec: ProblemSpec) -> tuple[Solution, Usage]:
    system = (
        "You are the Solver, an expert competitive programmer and patient teacher. Find the "
        "optimal approach, explain it as ordered reasoning steps a student can follow, then "
        "write clean, idiomatic Python with meaningful variable names (they are shown in an "
        "animated visualization). Avoid printing. " + PYTHON_ENV_NOTE
    )
    return await llm.structured(
        agent="solver", system=system, prompt=spec_block(spec),
        schema=Solution, tier="smart", temperature=0.2,
    )
