"""Build data/roadmaps.json: NeetCode 150 and Blind 75 as lists of facts.

Only titles, numbers, difficulty, pattern category and the function signature are stored
(no problem statements). Lessons are generated from the name, and the signature lets the
pipeline check it reconstructed the right problem.

Sources (credit and link in the UI): NeetCode 150 (neetcode.io/practice) and the original
Blind 75 list (teamblind.com).

    uv run python -m scripts.build_roadmaps
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# kind: "function" (supported) | "design" (class with a sequence of method calls)
#       | "special" (needs node structures beyond ListNode/TreeNode: cycles, random pointers,
#         graph nodes, node references as arguments)
# Rows: (number, title, difficulty, signature, blind75, kind[, neetcode150])
E, M, H = "easy", "medium", "hard"
CATEGORIES: list[tuple[str, list[tuple]]] = [
    ("Arrays & Hashing", [
        (217, "Contains Duplicate", E, "containsDuplicate(nums)", True, "function"),
        (242, "Valid Anagram", E, "isAnagram(s, t)", True, "function"),
        (1, "Two Sum", E, "twoSum(nums, target)", True, "function"),
        (49, "Group Anagrams", M, "groupAnagrams(strs)", True, "function"),
        (347, "Top K Frequent Elements", M, "topKFrequent(nums, k)", True, "function"),
        (271, "Encode and Decode Strings", M, "Codec", True, "design"),
        (238, "Product of Array Except Self", M, "productExceptSelf(nums)", True, "function"),
        (36, "Valid Sudoku", M, "isValidSudoku(board)", False, "function"),
        (128, "Longest Consecutive Sequence", M, "longestConsecutive(nums)", True, "function"),
    ]),
    ("Two Pointers", [
        (125, "Valid Palindrome", E, "isPalindrome(s)", True, "function"),
        (167, "Two Sum II - Input Array Is Sorted", M, "twoSum(numbers, target)", False, "function"),
        (15, "3Sum", M, "threeSum(nums)", True, "function"),
        (11, "Container With Most Water", M, "maxArea(height)", True, "function"),
        (42, "Trapping Rain Water", H, "trap(height)", False, "function"),
    ]),
    ("Sliding Window", [
        (121, "Best Time to Buy and Sell Stock", E, "maxProfit(prices)", True, "function"),
        (3, "Longest Substring Without Repeating Characters", M, "lengthOfLongestSubstring(s)", True, "function"),
        (424, "Longest Repeating Character Replacement", M, "characterReplacement(s, k)", True, "function"),
        (567, "Permutation in String", M, "checkInclusion(s1, s2)", False, "function"),
        (76, "Minimum Window Substring", H, "minWindow(s, t)", True, "function"),
        (239, "Sliding Window Maximum", H, "maxSlidingWindow(nums, k)", False, "function"),
    ]),
    ("Stack", [
        (20, "Valid Parentheses", E, "isValid(s)", True, "function"),
        (155, "Min Stack", M, "MinStack", False, "design"),
        (150, "Evaluate Reverse Polish Notation", M, "evalRPN(tokens)", False, "function"),
        (22, "Generate Parentheses", M, "generateParenthesis(n)", False, "function"),
        (739, "Daily Temperatures", M, "dailyTemperatures(temperatures)", False, "function"),
        (853, "Car Fleet", M, "carFleet(target, position, speed)", False, "function"),
        (84, "Largest Rectangle in Histogram", H, "largestRectangleArea(heights)", False, "function"),
    ]),
    ("Binary Search", [
        (704, "Binary Search", E, "search(nums, target)", False, "function"),
        (74, "Search a 2D Matrix", M, "searchMatrix(matrix, target)", False, "function"),
        (875, "Koko Eating Bananas", M, "minEatingSpeed(piles, h)", False, "function"),
        (153, "Find Minimum in Rotated Sorted Array", M, "findMin(nums)", True, "function"),
        (33, "Search in Rotated Sorted Array", M, "search(nums, target)", True, "function"),
        (981, "Time Based Key-Value Store", M, "TimeMap", False, "design"),
        (4, "Median of Two Sorted Arrays", H, "findMedianSortedArrays(nums1, nums2)", False, "function"),
    ]),
    ("Linked List", [
        (206, "Reverse Linked List", E, "reverseList(head)", True, "function"),
        (21, "Merge Two Sorted Lists", E, "mergeTwoLists(list1, list2)", True, "function"),
        (143, "Reorder List", M, "reorderList(head)", True, "function"),
        (19, "Remove Nth Node From End of List", M, "removeNthFromEnd(head, n)", True, "function"),
        (138, "Copy List with Random Pointer", M, "copyRandomList(head)", False, "special"),
        (2, "Add Two Numbers", M, "addTwoNumbers(l1, l2)", False, "function"),
        (141, "Linked List Cycle", E, "hasCycle(head)", True, "special"),
        (287, "Find the Duplicate Number", M, "findDuplicate(nums)", False, "function"),
        (146, "LRU Cache", M, "LRUCache", False, "design"),
        (23, "Merge k Sorted Lists", H, "mergeKLists(lists)", True, "function"),
        (25, "Reverse Nodes in k-Group", H, "reverseKGroup(head, k)", False, "function"),
    ]),
    ("Trees", [
        (226, "Invert Binary Tree", E, "invertTree(root)", True, "function"),
        (104, "Maximum Depth of Binary Tree", E, "maxDepth(root)", True, "function"),
        (543, "Diameter of Binary Tree", E, "diameterOfBinaryTree(root)", False, "function"),
        (110, "Balanced Binary Tree", E, "isBalanced(root)", False, "function"),
        (100, "Same Tree", E, "isSameTree(p, q)", True, "function"),
        (572, "Subtree of Another Tree", E, "isSubtree(root, subRoot)", True, "function"),
        (235, "Lowest Common Ancestor of a Binary Search Tree", M, "lowestCommonAncestor(root, p, q)", True, "special"),
        (102, "Binary Tree Level Order Traversal", M, "levelOrder(root)", True, "function"),
        (199, "Binary Tree Right Side View", M, "rightSideView(root)", False, "function"),
        (1448, "Count Good Nodes in Binary Tree", M, "goodNodes(root)", False, "function"),
        (98, "Validate Binary Search Tree", M, "isValidBST(root)", True, "function"),
        (230, "Kth Smallest Element in a BST", M, "kthSmallest(root, k)", True, "function"),
        (105, "Construct Binary Tree from Preorder and Inorder Traversal", M, "buildTree(preorder, inorder)", True, "function"),
        (124, "Binary Tree Maximum Path Sum", H, "maxPathSum(root)", True, "function"),
        (297, "Serialize and Deserialize Binary Tree", H, "Codec", True, "design"),
    ]),
    ("Heap / Priority Queue", [
        (703, "Kth Largest Element in a Stream", E, "KthLargest", False, "design"),
        (1046, "Last Stone Weight", E, "lastStoneWeight(stones)", False, "function"),
        (973, "K Closest Points to Origin", M, "kClosest(points, k)", False, "function"),
        (215, "Kth Largest Element in an Array", M, "findKthLargest(nums, k)", False, "function"),
        (621, "Task Scheduler", M, "leastInterval(tasks, n)", False, "function"),
        (355, "Design Twitter", M, "Twitter", False, "design"),
        (295, "Find Median from Data Stream", H, "MedianFinder", True, "design"),
    ]),
    ("Backtracking", [
        (78, "Subsets", M, "subsets(nums)", False, "function"),
        (39, "Combination Sum", M, "combinationSum(candidates, target)", False, "function"),
        (46, "Permutations", M, "permute(nums)", False, "function"),
        (90, "Subsets II", M, "subsetsWithDup(nums)", False, "function"),
        (40, "Combination Sum II", M, "combinationSum2(candidates, target)", False, "function"),
        (79, "Word Search", M, "exist(board, word)", True, "function"),
        (131, "Palindrome Partitioning", M, "partition(s)", False, "function"),
        (17, "Letter Combinations of a Phone Number", M, "letterCombinations(digits)", False, "function"),
        (51, "N-Queens", H, "solveNQueens(n)", False, "function"),
    ]),
    ("Tries", [
        (208, "Implement Trie (Prefix Tree)", M, "Trie", True, "design"),
        (211, "Design Add and Search Words Data Structure", M, "WordDictionary", True, "design"),
        (212, "Word Search II", H, "findWords(board, words)", True, "function"),
    ]),
    ("Graphs", [
        (200, "Number of Islands", M, "numIslands(grid)", True, "function"),
        (695, "Max Area of Island", M, "maxAreaOfIsland(grid)", False, "function"),
        (133, "Clone Graph", M, "cloneGraph(node)", True, "special"),
        (286, "Walls and Gates", M, "wallsAndGates(rooms)", False, "function"),
        (994, "Rotting Oranges", M, "orangesRotting(grid)", False, "function"),
        (417, "Pacific Atlantic Water Flow", M, "pacificAtlantic(heights)", True, "function"),
        (130, "Surrounded Regions", M, "solve(board)", False, "function"),
        (207, "Course Schedule", M, "canFinish(numCourses, prerequisites)", True, "function"),
        (210, "Course Schedule II", M, "findOrder(numCourses, prerequisites)", False, "function"),
        (684, "Redundant Connection", M, "findRedundantConnection(edges)", False, "function"),
        (323, "Number of Connected Components in an Undirected Graph", M, "countComponents(n, edges)", True, "function"),
        (261, "Graph Valid Tree", M, "validTree(n, edges)", True, "function"),
        (127, "Word Ladder", H, "ladderLength(beginWord, endWord, wordList)", False, "function"),
    ]),
    ("Advanced Graphs", [
        (332, "Reconstruct Itinerary", H, "findItinerary(tickets)", False, "function"),
        (1584, "Min Cost to Connect All Points", M, "minCostConnectPoints(points)", False, "function"),
        (743, "Network Delay Time", M, "networkDelayTime(times, n, k)", False, "function"),
        (778, "Swim in Rising Water", H, "swimInWater(grid)", False, "function"),
        (269, "Alien Dictionary", H, "alienOrder(words)", True, "function"),
        (787, "Cheapest Flights Within K Stops", M, "findCheapestPrice(n, flights, src, dst, k)", False, "function"),
    ]),
    ("1-D Dynamic Programming", [
        (70, "Climbing Stairs", E, "climbStairs(n)", True, "function"),
        (746, "Min Cost Climbing Stairs", E, "minCostClimbingStairs(cost)", False, "function"),
        (198, "House Robber", M, "rob(nums)", True, "function"),
        (213, "House Robber II", M, "rob(nums)", True, "function"),
        (5, "Longest Palindromic Substring", M, "longestPalindrome(s)", True, "function"),
        (647, "Palindromic Substrings", M, "countSubstrings(s)", True, "function"),
        (91, "Decode Ways", M, "numDecodings(s)", True, "function"),
        (322, "Coin Change", M, "coinChange(coins, amount)", True, "function"),
        (152, "Maximum Product Subarray", M, "maxProduct(nums)", True, "function"),
        (139, "Word Break", M, "wordBreak(s, wordDict)", True, "function"),
        (300, "Longest Increasing Subsequence", M, "lengthOfLIS(nums)", True, "function"),
        (416, "Partition Equal Subset Sum", M, "canPartition(nums)", False, "function"),
        (377, "Combination Sum IV", M, "combinationSum4(nums, target)", True, "function", False),
    ]),
    ("2-D Dynamic Programming", [
        (62, "Unique Paths", M, "uniquePaths(m, n)", True, "function"),
        (1143, "Longest Common Subsequence", M, "longestCommonSubsequence(text1, text2)", True, "function"),
        (309, "Best Time to Buy and Sell Stock with Cooldown", M, "maxProfit(prices)", False, "function"),
        (518, "Coin Change II", M, "change(amount, coins)", False, "function"),
        (494, "Target Sum", M, "findTargetSumWays(nums, target)", False, "function"),
        (97, "Interleaving String", M, "isInterleave(s1, s2, s3)", False, "function"),
        (329, "Longest Increasing Path in a Matrix", H, "longestIncreasingPath(matrix)", False, "function"),
        (115, "Distinct Subsequences", H, "numDistinct(s, t)", False, "function"),
        (72, "Edit Distance", M, "minDistance(word1, word2)", False, "function"),
        (312, "Burst Balloons", H, "maxCoins(nums)", False, "function"),
        (10, "Regular Expression Matching", H, "isMatch(s, p)", False, "function"),
    ]),
    ("Greedy", [
        (53, "Maximum Subarray", M, "maxSubArray(nums)", True, "function"),
        (55, "Jump Game", M, "canJump(nums)", True, "function"),
        (45, "Jump Game II", M, "jump(nums)", False, "function"),
        (134, "Gas Station", M, "canCompleteCircuit(gas, cost)", False, "function"),
        (846, "Hand of Straights", M, "isNStraightHand(hand, groupSize)", False, "function"),
        (1899, "Merge Triplets to Form Target Triplet", M, "mergeTriplets(triplets, target)", False, "function"),
        (763, "Partition Labels", M, "partitionLabels(s)", False, "function"),
        (678, "Valid Parenthesis String", M, "checkValidString(s)", False, "function"),
    ]),
    ("Intervals", [
        (57, "Insert Interval", M, "insert(intervals, newInterval)", True, "function"),
        (56, "Merge Intervals", M, "merge(intervals)", True, "function"),
        (435, "Non-overlapping Intervals", M, "eraseOverlapIntervals(intervals)", True, "function"),
        (252, "Meeting Rooms", E, "canAttendMeetings(intervals)", True, "function"),
        (253, "Meeting Rooms II", M, "minMeetingRooms(intervals)", True, "function"),
        (1851, "Minimum Interval to Include Each Query", H, "minInterval(intervals, queries)", False, "function"),
    ]),
    ("Math & Geometry", [
        (48, "Rotate Image", M, "rotate(matrix)", True, "function"),
        (54, "Spiral Matrix", M, "spiralOrder(matrix)", True, "function"),
        (73, "Set Matrix Zeroes", M, "setZeroes(matrix)", True, "function"),
        (202, "Happy Number", E, "isHappy(n)", False, "function"),
        (66, "Plus One", E, "plusOne(digits)", False, "function"),
        (50, "Pow(x, n)", M, "myPow(x, n)", False, "function"),
        (43, "Multiply Strings", M, "multiply(num1, num2)", False, "function"),
        (2013, "Detect Squares", M, "DetectSquares", False, "design"),
    ]),
    ("Bit Manipulation", [
        (136, "Single Number", E, "singleNumber(nums)", False, "function"),
        (191, "Number of 1 Bits", E, "hammingWeight(n)", True, "function"),
        (338, "Counting Bits", E, "countBits(n)", True, "function"),
        (190, "Reverse Bits", E, "reverseBits(n)", True, "function"),
        (268, "Missing Number", E, "missingNumber(nums)", True, "function"),
        (371, "Sum of Two Integers", M, "getSum(a, b)", True, "function"),
        (7, "Reverse Integer", M, "reverse(x)", False, "function"),
    ]),
]

# LeetCode Premium problems (NeetCode hosts free versions); linked for reference only.
PREMIUM = {271, 252, 253, 261, 269, 286, 323}


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    return re.sub(r"[\s-]+", "-", s).strip("-")


def parse_signature(sig: str) -> dict:
    m = re.fullmatch(r"(\w+)\((.*)\)", sig)
    if not m:
        return {"class_name": sig}
    params = [p.strip() for p in m.group(2).split(",") if p.strip()]
    return {"entry": m.group(1), "params": params}


def build() -> dict:
    problems = []
    for category, rows in CATEGORIES:
        for row in rows:
            number, title, difficulty, sig, blind, kind = row[:6]
            neetcode = row[6] if len(row) > 6 else True
            slug = slugify(title)
            problems.append({
                "id": slug, "number": number, "title": title, "difficulty": difficulty,
                "category": category, "kind": kind, **parse_signature(sig),
                "roadmaps": [r for r, on in (("neetcode150", neetcode), ("blind75", blind)) if on],
                "premium": number in PREMIUM,
                "url": f"https://leetcode.com/problems/{slug}/",
            })
    return {
        "roadmaps": [
            {"id": "blind75", "title": "Blind 75", "source": "Original list by a Blind user (2018)",
             "source_url": "https://www.teamblind.com/post/New-Year-Gift---Curated-List-of-Top-75-LeetCode-Questions-to-Save-Your-Time-OaM1orEU"},
            {"id": "neetcode150", "title": "NeetCode 150", "source": "NeetCode",
             "source_url": "https://neetcode.io/practice"},
        ],
        "categories": [c for c, _ in CATEGORIES],
        "problems": problems,
    }


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "cotutor" / "data" / "roadmaps.json"
    data = build()
    out.write_text(json.dumps(data, indent=1) + "\n")
    counts = {r["id"]: sum(r["id"] in p["roadmaps"] for p in data["problems"]) for r in data["roadmaps"]}
    kinds = {k: sum(p["kind"] == k for p in data["problems"]) for k in ("function", "design", "special")}
    print(f"wrote {out.name}: {len(data['problems'])} problems, {counts}, {kinds}")
