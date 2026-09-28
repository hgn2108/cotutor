"""Referee: settles a disagreement between the solution and the brute-force reference.

Both were written by agents, so either can be wrong. The Referee never sees their code: only
the problem, one input and the two outputs in random order, and it works the answer out from
the statement. That independence is the point: it can't inherit either author's misreading.
"""

from __future__ import annotations

import hashlib
import json

from ..llm import LLMClient, Usage
from ..schemas import ProblemSpec, RefereeVerdict
from .common import spec_block


async def referee(
    llm: LLMClient, spec: ProblemSpec, statement: str, args: object, reference_out: object,
    solution_out: object,
) -> tuple[str, str, Usage]:
    """Return ("reference" | "solution" | "neither", reasoning, usage)."""
    # Deterministic but unbiased order, so "A" isn't always the reference.
    swap = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).digest()[0] % 2 == 1
    a, b = (solution_out, reference_out) if swap else (reference_out, solution_out)
    system = (
        "You are the Referee. Two programs disagree on one input. Work out the correct output "
        "yourself, strictly from the problem statement: trace the input step by step, paying "
        "close attention to boundaries (inclusive vs exclusive ranges, ties, duplicates, empty "
        "inputs). Then say which candidate matches, or 'neither'."
    )
    prompt = (
        (f"Original problem statement:\n{statement.strip()}\n\n" if statement.strip() else "")
        + f"{spec_block(spec)}\n\nInput (JSON arguments): {json.dumps(args)[:3000]}\n\n"
        f"Candidate A output: {json.dumps(a)[:1500]}\nCandidate B output: {json.dumps(b)[:1500]}"
    )
    verdict, usage = await llm.structured(
        agent="referee", system=system, prompt=prompt, schema=RefereeVerdict, tier="smart", temperature=0,
    )
    pick = {"A": "solution" if swap else "reference", "B": "reference" if swap else "solution"}
    return pick.get(verdict.correct, "neither"), verdict.reasoning, usage
