"""Analyst: turns an informal problem statement into a precise, checkable spec."""

from __future__ import annotations

from ..llm import LLMClient, Usage
from ..schemas import ProblemSpec
from .common import PYTHON_ENV_NOTE


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
