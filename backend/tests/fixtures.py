"""Scripted agent responses for Two Sum.

The first solution has a deliberate bug (it "prunes" values above target), which only the
random stress test catches and the debugger must fix."""

from cotutor.schemas import (
    DebugResult,
    Example,
    Explanation,
    FlowEdge,
    FlowNode,
    LessonDeep,
    LessonIntro,
    LineCost,
    Param,
    PatternOption,
    ProblemSpec,
    ReasoningStep,
    Signal,
    Solution,
    TestCaseDraft,
    TestPlan,
    VizVar,
)

SPEC = ProblemSpec(
    is_solvable=True, title="Two Sum",
    summary="Given an integer array nums and an integer target, return the indices of two "
            "different elements that add up to target. Exactly one answer exists.",
    entry="twoSum",
    params=[Param(name="nums", type="List[int]"), Param(name="target", type="int")],
    return_type="List[int]",
    examples=[Example(args_json="[[2,7,11,15],9]", expected_json="[0,1]"),
              Example(args_json="[[3,2,4],6]", expected_json="[1,2]")],
    constraints=["2 <= len(nums) <= 10^4", "exactly one valid answer"],
    comparison="unordered", multiple_valid_answers=True, in_place_arg=-1,
    pattern_tags=["hash map"], difficulty="easy",
)

PLAN = TestPlan(
    cases=[TestCaseDraft(name="negatives", category="edge", args_json="[[-3,4,3,90],0]",
                         rationale="negative numbers"),
           TestCaseDraft(name="duplicates", category="tricky", args_json="[[3,3],6]",
                         rationale="same value twice"),
           TestCaseDraft(name="not a list", category="edge", args_json="{bad json",
                         rationale="malformed input should be dropped")],
    reference_solution=(
        "def twoSum(nums, target):\n"
        "    for i in range(len(nums)):\n"
        "        for j in range(i + 1, len(nums)):\n"
        "            if nums[i] + nums[j] == target:\n"
        "                return [i, j]\n"
    ),
    reference_time_complexity="O(n^2)",
    generator_code=(
        "def generate(rng, n):\n"
        "    n = max(2, n)\n"
        "    nums = [rng.randint(-20, 20) for _ in range(n)]\n"
        "    i, j = rng.sample(range(n), 2)\n"
        "    return [nums, nums[i] + nums[j]]\n\n"
        "def generate_worst(rng, n):\n"
        "    return [list(range(1, n + 1)), 2 * n - 1]\n"
    ),
    checker_code=(
        "def check(args, got, expected):\n"
        "    nums, target = args\n"
        "    return (isinstance(got, list) and len(got) == 2 and got[0] != got[1]\n"
        "            and nums[got[0]] + nums[got[1]] == target)\n"
    ),
)

# Passes every example and hand-written case; only random inputs with two negatives expose it.
BUGGY_CODE = (
    "class Solution:\n"
    "    def twoSum(self, nums, target):\n"
    "        index_of = {x: i for i, x in enumerate(nums)}\n"
    "        for i, x in enumerate(nums):\n"
    "            if x > target:  # 'pruning' that silently assumes non-negative numbers\n"
    "                continue\n"
    "            j = index_of.get(target - x)\n"
    "            if j is not None and j != i:\n"
    "                return [i, j]\n"
)

FIXED_CODE = (
    "class Solution:\n"
    "    def twoSum(self, nums, target):\n"
    "        seen = {}\n"
    "        for i, x in enumerate(nums):\n"
    "            if target - x in seen:\n"
    "                return [seen[target - x], i]\n"
    "            seen[x] = i\n"
)

SOLUTION = Solution(
    approach="Hash map of seen values", key_insight="Look up each number's complement.",
    steps=[ReasoningStep(title="Index values", detail="Map each value to its index."),
           ReasoningStep(title="Find complement", detail="Check target - x in the map.")],
    code=BUGGY_CODE, time_complexity="O(n)", space_complexity="O(n)",
)

DEBUG = DebugResult(
    diagnosis="Skipping x > target is wrong when numbers can be negative.",
    blame="solution", code=FIXED_CODE,
    fix_summary="Remove the pruning; do a single pass over values seen so far.",
)

EXPLANATION = Explanation(
    overview="Walk the array once, remembering each value's index in a hash map.",
    intuition="Like checking a guest list for the partner you need.",
    flow_nodes=[FlowNode(id="n1", label="Start", kind="start", detail=""),
                FlowNode(id="n2", label="For each x", kind="loop", detail=""),
                FlowNode(id="n3", label="Complement seen?", kind="decision", detail=""),
                FlowNode(id="n4", label="Return pair", kind="end", detail=""),
                FlowNode(id="n5", label="Store x", kind="step", detail="")],
    flow_edges=[FlowEdge(source="n1", target="n2", label=""),
                FlowEdge(source="n2", target="n3", label=""),
                FlowEdge(source="n3", target="n4", label="yes"),
                FlowEdge(source="n3", target="n5", label="no"),
                FlowEdge(source="n5", target="n2", label="next")],
    pitfalls=["Pairing an element with itself."],
    viz_vars=[VizVar(name="nums", role="array", target=""),
              VizVar(name="i", role="pointer", target="nums"),
              VizVar(name="seen", role="hashmap", target="")],
    viz_args_json="[[3,2,4,7],6]",
    similar_problems=["3Sum"],
)

LESSON_INTRO = LessonIntro(
    pattern="Hash map lookup",
    pattern_summary="Store what you've already seen in a dictionary so that 'have I seen X?' "
                    "takes constant time instead of a scan.",
    pattern_options=[
        PatternOption(name="Hash map lookup", correct=True,
                      feedback="Each number needs one specific partner (target - x). A dictionary "
                               "answers 'have I seen that partner?' instantly."),
        PatternOption(name="Two pointers on a sorted array", correct=False,
                      feedback="Works for the sum, but sorting loses the original indices you must "
                               "return, and costs O(n log n)."),
        PatternOption(name="Sliding window", correct=False,
                      feedback="Windows are for contiguous ranges; the two numbers can be anywhere."),
        PatternOption(name="Dynamic programming", correct=False,
                      feedback="There are no overlapping subproblems to build up; it's a lookup."),
    ],
    signals=[Signal(phrase="two different elements", hint="You're looking for a pair."),
             Signal(phrase="whose sum equals target",
                    hint="Fixing one number fixes its partner exactly: target - x."),
             Signal(phrase="return the indices", hint="You must remember positions, not just values.")],
    brute_force_idea="Try every pair (i, j) with i < j and check whether they add up to target.",
    brute_force_time="O(n²)",
    brute_force_why="For each of the n elements, the inner loop scans the rest: n·(n-1)/2 pairs.",
    bottleneck_line=3,
    bottleneck="For every i, the inner loop re-scans the array looking for one specific value, "
               "target - nums[i]. The same elements get searched over and over.",
    bottleneck_hints=["Which line runs the most times as the array grows?",
                      "For a fixed i, what exact value is the inner loop searching for?",
                      "Searching for a known value by scanning is slow. What finds a value instantly?"],
)

LESSON_DEEP = LessonDeep(
    insight="Instead of re-scanning for target - x, remember every value seen so far in a "
            "dictionary. Checking for the partner becomes one O(1) lookup, so the inner loop "
            "disappears.",
    derivation=[LineCost(line=4, cost="n times", note="One pass over the array."),
                LineCost(line=5, cost="O(1) average", note="Dictionary membership is a hash lookup."),
                LineCost(line=7, cost="O(1) average", note="Dictionary insert is a hash write.")],
    time_summary="n iterations × O(1) work each = O(n). The step counts double when n doubles "
                 "(linear), while the brute force quadruples (quadratic).",
    space_summary="The dictionary can hold up to n entries: O(n) extra space.",
    takeaway="When each element needs one specific partner, store what you've seen in a hash "
             "map and look the partner up instead of searching for it.",
    mistakes=["Building the whole map first can pair an element with itself (target = 2·x).",
              "Assuming numbers are non-negative and pruning with x > target."],
)


def two_sum_script():
    return {"analyst": [SPEC], "test_designer": [PLAN], "solver": [SOLUTION],
            "debugger": [DEBUG], "tutor": [EXPLANATION], "coach_intro": [LESSON_INTRO],
            "coach_deep": [LESSON_DEEP]}
