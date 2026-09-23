"""Prompt building blocks shared by every agent."""

from __future__ import annotations

from ..schemas import ProblemSpec

PYTHON_ENV_NOTE = (
    "Code runs on CPython 3.12 with only the standard library. `List`, `Optional`, "
    "`collections`, `heapq`, `bisect`, `math`, `functools`, `itertools` and LeetCode's "
    "`ListNode(val, next)` / `TreeNode(val, left, right)` are pre-imported. ListNode/TreeNode "
    "arguments are passed as real nodes; in JSON they are written as lists (trees in "
    "LeetCode level order with null)."
)


def spec_block(spec: ProblemSpec) -> str:
    params = ", ".join(f"{p.name}: {p.type}" for p in spec.params)
    examples = "\n".join(f"  args={e.args_json} -> {e.expected_json}" for e in spec.examples)
    return (
        f"Title: {spec.title}\nTask: {spec.summary}\n"
        f"Signature: def {spec.entry}({params}) -> {spec.return_type}\n"
        f"Constraints: {'; '.join(spec.constraints) or 'none given'}\n"
        f"Examples:\n{examples}"
    )


def numbered(code: str) -> str:
    return "\n".join(f"{i:>3} | {line}" for i, line in enumerate(code.rstrip().split("\n"), 1))
