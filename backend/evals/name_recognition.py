"""Can the Analyst reconstruct a well-known problem from its name alone?

Roadmap lessons start from "LeetCode <n>: <title>" instead of the copyrighted statement, so
this checks the reconstructed spec against the problem's real function signature.

    uv run python -m evals.name_recognition
"""

from __future__ import annotations

import asyncio
import time

from cotutor import agents
from cotutor.config import settings
from cotutor.llm import GeminiClient

# (number, title, entry, params). Function signatures are facts, not problem text.
CASES = [
    (1, "Two Sum", "twoSum", ["nums", "target"]),
    (49, "Group Anagrams", "groupAnagrams", ["strs"]),
    (238, "Product of Array Except Self", "productExceptSelf", ["nums"]),
    (128, "Longest Consecutive Sequence", "longestConsecutive", ["nums"]),
    (424, "Longest Repeating Character Replacement", "characterReplacement", ["s", "k"]),
    (76, "Minimum Window Substring", "minWindow", ["s", "t"]),
    (875, "Koko Eating Bananas", "minEatingSpeed", ["piles", "h"]),
    (153, "Find Minimum in Rotated Sorted Array", "findMin", ["nums"]),
    (143, "Reorder List", "reorderList", ["head"]),
    (572, "Subtree of Another Tree", "isSubtree", ["root", "subRoot"]),
    (230, "Kth Smallest Element in a BST", "kthSmallest", ["root", "k"]),
    (39, "Combination Sum", "combinationSum", ["candidates", "target"]),
    (207, "Course Schedule", "canFinish", ["numCourses", "prerequisites"]),
    (70, "Climbing Stairs", "climbStairs", ["n"]),
    (322, "Coin Change", "coinChange", ["coins", "amount"]),
    (300, "Longest Increasing Subsequence", "lengthOfLIS", ["nums"]),
    (57, "Insert Interval", "insert", ["intervals", "newInterval"]),
    (191, "Number of 1 Bits", "hammingWeight", ["n"]),
    (1143, "Longest Common Subsequence", "longestCommonSubsequence", ["text1", "text2"]),
    (416, "Partition Equal Subset Sum", "canPartition", ["nums"]),
]


async def main() -> None:
    llm = GeminiClient(settings.gemini_api_key, settings.smart_models, settings.fast_models)
    ok = 0
    t0 = time.perf_counter()
    for number, title, entry, params in CASES:
        spec, usage = await agents.analyze(llm, f"LeetCode {number}: {title}")
        got = [p.name for p in spec.params]
        good = spec.entry == entry and got == params and spec.is_solvable
        ok += good
        flag = "ok " if good else "BAD"
        print(f"{flag} {number:>5} {title:<42} {spec.entry}({', '.join(got)})  "
              f"{len(spec.examples)} ex  {usage.model}  {usage.ms / 1000:.1f}s")
    print(f"\n{ok}/{len(CASES)} signatures reconstructed exactly  ·  {time.perf_counter() - t0:.0f}s total")


if __name__ == "__main__":
    asyncio.run(main())
