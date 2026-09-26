"""Analyst: turns an informal problem statement into a precise, checkable spec."""

from __future__ import annotations

from ..llm import LLMClient, Usage
from ..schemas import ProblemSpec
from .common import DESIGN_NOTE, PYTHON_ENV_NOTE


async def analyze(llm: LLMClient, problem: str) -> tuple[ProblemSpec, Usage]:
    system = (
        "You are the Analyst in an algorithm-tutoring system. Turn a user's problem statement "
        "(often informal or copied from LeetCode) into a precise, machine-checkable spec. "
        "If the statement gives a function or class signature, use it exactly (names and "
        "argument order). Otherwise use LeetCode's conventional name and argument order when the "
        "problem is a known one. If the input only names a well-known problem (e.g. 'LeetCode 1: Two Sum'), "
        "reconstruct its full specification from your knowledge and use the given function "
        "signature exactly. Write the summary in your own words in the Input / Output / Rules "
        "shape; never reproduce the original statement's phrasing, story or character names. "
        "Mark each example from_statement=True only if it appears in the user's text. Set "
        "unsupported_reason instead of forcing a spec for problems that can't be verified by "
        "running a Python function or class. Every example's expected output must be "
        "exactly right: prefer small "
        "examples you can verify by hand. " + DESIGN_NOTE + " " + PYTHON_ENV_NOTE
    )
    return await llm.structured(
        agent="analyst", system=system, prompt=f"Problem statement:\n{problem}",
        schema=ProblemSpec, tier="fast", temperature=0.1,
    )
