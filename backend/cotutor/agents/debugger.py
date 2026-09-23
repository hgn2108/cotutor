"""Debugger: fixes a solution from concrete failing cases."""

from __future__ import annotations

import json

from ..llm import LLMClient, Usage
from ..schemas import DebugResult, ProblemSpec, Solution
from .common import PYTHON_ENV_NOTE, spec_block


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
        f"{spec_block(spec)}\n\nCurrent code:\n```python\n{solution.code}\n```\n\n"
        f"Failing cases:\n{json.dumps(failures, indent=1)[:6000]}"
    )
    if history:
        prompt += "\n\nPrevious fix attempts that did NOT work:\n- " + "\n- ".join(history)
    return await llm.structured(
        agent="debugger", system=system, prompt=prompt, schema=DebugResult,
        tier="smart", temperature=0.2,
    )
