"""Tutor: flowchart of the real control flow and a plan for the animation."""

from __future__ import annotations

from ..llm import LLMClient, Usage
from ..schemas import Explanation, ProblemSpec, Solution
from .common import spec_block


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
        f"{spec_block(spec)}\n\nApproach: {solution.approach}\nKey insight: "
        f"{solution.key_insight}\nCode:\n```python\n{solution.code}\n```"
    )
    return await llm.structured(
        agent="tutor", system=system, prompt=prompt, schema=Explanation,
        tier="fast", temperature=0.4,
    )
