"""Structured outputs the agents must produce.

These are passed to the LLM as response schemas, so they stay within what structured-output
APIs support well: no free-form dicts, JSON values travel as strings (``*_json`` fields) and
are parsed and validated in code.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Comparison = Literal["exact", "unordered", "unordered_nested", "float"]


class Param(BaseModel):
    name: str
    type: str = Field(description="Python type hint, e.g. 'List[int]', 'Optional[TreeNode]'.")


class Example(BaseModel):
    args_json: str = Field(description="JSON array of positional arguments, e.g. '[[2,7,11,15], 9]'.")
    expected_json: str = Field(description="JSON of the expected return value.")


class ProblemSpec(BaseModel):
    is_solvable: bool = Field(description="False if the input is not a well-defined coding problem.")
    title: str
    summary: str = Field(description="Precise 2-4 sentence restatement of the task.")
    entry: str = Field(description="Function/method name, LeetCode style (e.g. 'twoSum').")
    params: list[Param]
    return_type: str
    examples: list[Example] = Field(description="2-4 examples with verified expected outputs.")
    constraints: list[str]
    comparison: Comparison = Field(
        description="exact | unordered (top-level order irrelevant) | unordered_nested "
        "(inner lists too, e.g. 3Sum) | float."
    )
    multiple_valid_answers: bool = Field(
        description="True when several different outputs are all correct (e.g. any valid index "
        "pair), so a custom checker is needed."
    )
    in_place_arg: int = Field(
        description="Index of the argument the function modifies in place when it returns "
        "nothing; -1 otherwise."
    )
    pattern_tags: list[str] = Field(description="e.g. ['hash map', 'two pointers'].")
    difficulty: Literal["easy", "medium", "hard"]


class TestCaseDraft(BaseModel):
    name: str
    category: Literal["edge", "tricky", "large"]
    args_json: str = Field(description="JSON array of positional arguments.")
    rationale: str = Field(description="What bug this input would catch.")


class TestPlan(BaseModel):
    cases: list[TestCaseDraft] = Field(description="6-10 inputs; do NOT include expected outputs.")
    reference_solution: str = Field(
        description="Brute-force Python solution that is obviously correct, even if slow. "
        "Must define a top-level function with the entry name."
    )
    generator_code: str = Field(
        description="Python defining generate(rng, n) -> list of args (random valid input of "
        "size n) and generate_worst(rng, n) -> list of args (worst case for runtime)."
    )
    checker_code: str = Field(
        description="If multiple answers are valid: Python defining "
        "check(args, got, expected) -> bool. Otherwise an empty string."
    )


class ReasoningStep(BaseModel):
    title: str
    detail: str


class Solution(BaseModel):
    approach: str = Field(description="Name of the approach, e.g. 'One-pass hash map'.")
    key_insight: str
    steps: list[ReasoningStep]
    code: str = Field(description="Complete Python solution (class Solution style is fine).")
    time_complexity: str = Field(description="Big-O in terms of n, e.g. 'O(n log n)'.")
    space_complexity: str


class DebugResult(BaseModel):
    diagnosis: str = Field(description="Root cause in 1-3 sentences.")
    blame: Literal["solution", "test"] = Field(
        description="'test' only if you are certain the expected output is wrong."
    )
    fix_summary: str
    code: str = Field(description="Full corrected solution (unchanged if blame='test').")


class FlowNode(BaseModel):
    id: str
    label: str = Field(description="At most 6 words.")
    kind: Literal["start", "step", "decision", "loop", "end"]
    detail: str = Field(description="One sentence shown on hover.")


class FlowEdge(BaseModel):
    source: str
    target: str
    label: str = Field(description="Short label such as 'yes', 'no', 'next i'; may be empty.")


class VizVar(BaseModel):
    name: str = Field(description="Exact variable name in the code.")
    role: Literal[
        "array", "pointer", "hashmap", "set", "grid", "stack", "queue",
        "linked_list", "tree", "scalar",
    ]
    target: str = Field(description="For role='pointer': the array it indexes. Else ''.")


class Explanation(BaseModel):
    overview: str = Field(description="2-3 sentences: what the algorithm does and why it works.")
    intuition: str = Field(description="A concrete analogy or mental picture.")
    flow_nodes: list[FlowNode]
    flow_edges: list[FlowEdge]
    pitfalls: list[str] = Field(description="2-4 common mistakes.")
    viz_vars: list[VizVar] = Field(description="Variables worth visualizing, most important first.")
    viz_args_json: str = Field(description="Small illustrative input (JSON args) for animation.")
    similar_problems: list[str]


# --------------------------------------------------------------------------------------
# Coach: pedagogy. Teaches the reasoning path (signals → brute force → bottleneck →
# insight → why the complexity is what it is) rather than handing over the answer.
# --------------------------------------------------------------------------------------
class PatternOption(BaseModel):
    name: str = Field(description="A general technique, e.g. 'Hash map lookup', 'Two pointers'.")
    correct: bool
    feedback: str = Field(description="1-2 sentences: why it fits, or why it doesn't fit here.")


class Signal(BaseModel):
    phrase: str = Field(description="A short phrase copied EXACTLY from the problem statement.")
    hint: str = Field(description="What this phrase suggests about the approach.")


class LessonIntro(BaseModel):
    pattern: str = Field(description="Name of the core pattern (must equal the correct option's name).")
    pattern_summary: str = Field(description="What the pattern is and when to reach for it, in general.")
    pattern_options: list[PatternOption] = Field(description="Exactly 4 plausible options, one correct.")
    signals: list[Signal] = Field(description="2-4 phrases in the problem that hint at the pattern.")
    brute_force_idea: str = Field(description="The most direct approach, in 1-3 sentences.")
    brute_force_time: str = Field(description="Big-O of the brute force, e.g. 'O(n²)'.")
    brute_force_why: str = Field(description="Why the brute force has that complexity.")
    bottleneck_line: int = Field(description="1-based line number in the brute-force code where the "
                                             "repeated work happens.")
    bottleneck: str = Field(description="What work is repeated and why that's wasteful.")
    bottleneck_hints: list[str] = Field(
        description="3 hints, increasingly specific, that lead a student to the bottleneck "
        "without stating it outright."
    )


class LineCost(BaseModel):
    line: int = Field(description="1-based line number in the optimized code.")
    cost: str = Field(description="How often it runs or what it costs, e.g. 'n times', 'O(1) avg'.")
    note: str = Field(description="Why, in one short sentence.")


class LessonDeep(BaseModel):
    insight: str = Field(description="How the optimized approach removes the bottleneck (2-4 sentences).")
    derivation: list[LineCost] = Field(description="The lines that determine the complexity.")
    time_summary: str = Field(description="Walk from the line costs to the final time complexity.")
    space_summary: str = Field(description="What extra memory is used and why.")
    takeaway: str = Field(description="One memorable rule for recognizing and applying this pattern.")
    mistakes: list[str] = Field(description="2-4 common mistakes, including any bug found while "
                                            "verifying this solution.")
