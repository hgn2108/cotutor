"""Coach: the pedagogy. Pattern, brute force, bottleneck, then why the complexity holds."""

from __future__ import annotations

from ..llm import LLMClient, Usage
from ..schemas import LessonDeep, LessonIntro, ProblemSpec, Solution
from .common import numbered, spec_block

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
        f"Original problem statement:\n{problem}\n\n{spec_block(spec)}\n\n"
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
        f"{spec_block(spec)}\n\nBrute force:\n{numbered(brute_force)}\n\n"
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
