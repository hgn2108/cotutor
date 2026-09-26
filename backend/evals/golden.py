"""Independent ground truth for evaluating the pipeline.

Each entry is a hand-written, known-correct solution plus hidden test inputs (edge cases picked
to break wrong solutions), the optimal time complexity and the pattern. Expected outputs are
computed by running the golden solution, never by the pipeline, so the pipeline can't grade
itself. ``checks`` are known answers used to test the goldens themselves (see
tests/test_evals.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

L, T = "Optional[ListNode]", "Optional[TreeNode]"


@dataclass(frozen=True)
class Golden:
    id: str                                  # roadmap problem id
    entry: str                               # function name, or class name for design problems
    params: list[tuple[str, str]]
    code: str
    cases: list[list[Any]]                   # hidden inputs (positional args)
    checks: list[tuple[list[Any], Any]]      # (args, known answer) to validate the golden itself
    time: str                                # optimal time complexity
    patterns: tuple[str, ...]                # accepted keywords for the lesson's pattern
    return_type: str = ""
    comparison: str = "exact"
    kind: str = "function"
    in_place_arg: int | None = None
    checker: str = ""
    statement: str = ""                      # novel problems: the text the pipeline receives
    extra: dict = field(default_factory=dict)

    def spec(self) -> dict[str, Any]:
        return {"entry": self.entry, "kind": self.kind, "comparison": self.comparison,
                "return_type": self.return_type, "in_place_arg": self.in_place_arg,
                "params": [{"name": n, "type": t} for n, t in self.params]}


INTS = "List[int]"
GOLDEN: list[Golden] = [
    # ---------------------------------------------------------------- Arrays & Hashing
    Golden("two-sum", "twoSum", [("nums", INTS), ("target", "int")], """
def twoSum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
""", [[[2, 7, 11, 15], 9], [[3, 3], 6], [[-1, -2, -3, -4, -5], -8], [[0, 4, 3, 0], 0], [[1, 5, 9, 2], 11]],
        [([[2, 7, 11, 15], 9], [0, 1])], "O(n)", ("hash",), comparison="unordered"),
    Golden("contains-duplicate", "containsDuplicate", [("nums", INTS)], """
def containsDuplicate(nums):
    return len(set(nums)) != len(nums)
""", [[[1, 2, 3, 1]], [[1, 2, 3, 4]], [[1]], [[1, 1, 1, 3, 3, 4, 3, 2, 4, 2]], [[-1, 0, -1]]],
        [([[1, 2, 3, 1]], True), ([[1, 2, 3, 4]], False)], "O(n)", ("hash", "set")),
    Golden("valid-anagram", "isAnagram", [("s", "str"), ("t", "str")], """
def isAnagram(s, t):
    return sorted(s) == sorted(t)
""", [["anagram", "nagaram"], ["rat", "car"], ["a", "ab"], ["aacc", "ccac"], ["a", "a"]],
        [(["anagram", "nagaram"], True), (["rat", "car"], False)], "O(n)", ("hash", "count", "frequen")),
    Golden("group-anagrams", "groupAnagrams", [("strs", "List[str]")], """
def groupAnagrams(strs):
    groups = {}
    for s in strs:
        groups.setdefault("".join(sorted(s)), []).append(s)
    return list(groups.values())
""", [[["eat", "tea", "tan", "ate", "nat", "bat"]], [[""]], [["a"]], [["abc", "bca", "cab", "xyz", "zyx", "q"]], [["", ""]]],
        [([["eat", "tea", "tan", "ate", "nat", "bat"]], [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]])],
        "O(n k log k)", ("hash",), comparison="unordered_nested"),
    Golden("product-of-array-except-self", "productExceptSelf", [("nums", INTS)], """
def productExceptSelf(nums):
    out = [1] * len(nums)
    for i in range(1, len(nums)):
        out[i] = out[i - 1] * nums[i - 1]
    right = 1
    for i in range(len(nums) - 1, -1, -1):
        out[i] *= right
        right *= nums[i]
    return out
""", [[[1, 2, 3, 4]], [[-1, 1, 0, -3, 3]], [[0, 0]], [[2, 3]], [[5, 0, 2]]],
        [([[1, 2, 3, 4]], [24, 12, 8, 6]), ([[-1, 1, 0, -3, 3]], [0, 0, 9, 0, 0])], "O(n)", ("prefix",)),
    Golden("longest-consecutive-sequence", "longestConsecutive", [("nums", INTS)], """
def longestConsecutive(nums):
    s, best = set(nums), 0
    for x in s:
        if x - 1 not in s:
            y = x
            while y + 1 in s:
                y += 1
            best = max(best, y - x + 1)
    return best
""", [[[100, 4, 200, 1, 3, 2]], [[0, 3, 7, 2, 5, 8, 4, 6, 0, 1]], [[]], [[1, 2, 0, 1]], [[9, 1, -3, 2, 4, 8, 3, -1, 6, -2, -4, 7]]],
        [([[100, 4, 200, 1, 3, 2]], 4), ([[0, 3, 7, 2, 5, 8, 4, 6, 0, 1]], 9)], "O(n)", ("hash", "set")),
    # ---------------------------------------------------------------- Two Pointers
    Golden("valid-palindrome", "isPalindrome", [("s", "str")], """
def isPalindrome(s):
    t = [c.lower() for c in s if c.isalnum()]
    return t == t[::-1]
""", [["A man, a plan, a canal: Panama"], ["race a car"], [" "], ["0P"], [".,"], ["ab_a"]],
        [(["A man, a plan, a canal: Panama"], True), (["race a car"], False)], "O(n)", ("two pointer",)),
    Golden("3sum", "threeSum", [("nums", INTS)], """
def threeSum(nums):
    nums.sort()
    out = []
    for i in range(len(nums)):
        if i and nums[i] == nums[i - 1]:
            continue
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                out.append([nums[i], nums[lo], nums[hi]])
                lo += 1
                while lo < hi and nums[lo] == nums[lo - 1]:
                    lo += 1
    return out
""", [[[-1, 0, 1, 2, -1, -4]], [[0, 1, 1]], [[0, 0, 0]], [[0, 0, 0, 0]], [[-2, 0, 1, 1, 2]], [[1, -1, -1, 0]]],
        [([[-1, 0, 1, 2, -1, -4]], [[-1, -1, 2], [-1, 0, 1]]), ([[0, 1, 1]], [])], "O(n^2)",
        ("two pointer",), comparison="unordered_nested"),
    Golden("container-with-most-water", "maxArea", [("height", INTS)], """
def maxArea(height):
    lo, hi, best = 0, len(height) - 1, 0
    while lo < hi:
        best = max(best, (hi - lo) * min(height[lo], height[hi]))
        if height[lo] < height[hi]:
            lo += 1
        else:
            hi -= 1
    return best
""", [[[1, 8, 6, 2, 5, 4, 8, 3, 7]], [[1, 1]], [[4, 3, 2, 1, 4]], [[1, 2, 1]], [[2, 3, 4, 5, 18, 17, 6]]],
        [([[1, 8, 6, 2, 5, 4, 8, 3, 7]], 49), ([[1, 1]], 1)], "O(n)", ("two pointer",)),
    # ---------------------------------------------------------------- Sliding Window
    Golden("best-time-to-buy-and-sell-stock", "maxProfit", [("prices", INTS)], """
def maxProfit(prices):
    low, best = float("inf"), 0
    for p in prices:
        low = min(low, p)
        best = max(best, p - low)
    return best
""", [[[7, 1, 5, 3, 6, 4]], [[7, 6, 4, 3, 1]], [[1]], [[2, 4, 1]], [[3, 2, 6, 5, 0, 3]]],
        [([[7, 1, 5, 3, 6, 4]], 5), ([[7, 6, 4, 3, 1]], 0)], "O(n)", ("window", "greedy", "one pass", "minimum", "track")),
    Golden("longest-substring-without-repeating-characters", "lengthOfLongestSubstring", [("s", "str")], """
def lengthOfLongestSubstring(s):
    last, start, best = {}, 0, 0
    for i, c in enumerate(s):
        if last.get(c, -1) >= start:
            start = last[c] + 1
        last[c] = i
        best = max(best, i - start + 1)
    return best
""", [["abcabcbb"], ["bbbbb"], ["pwwkew"], [""], [" "], ["dvdf"], ["abba"]],
        [(["abcabcbb"], 3), (["pwwkew"], 3)], "O(n)", ("window",)),
    Golden("longest-repeating-character-replacement", "characterReplacement", [("s", "str"), ("k", "int")], """
def characterReplacement(s, k):
    count, left, top, best = {}, 0, 0, 0
    for right, c in enumerate(s):
        count[c] = count.get(c, 0) + 1
        top = max(top, count[c])
        while right - left + 1 - top > k:
            count[s[left]] -= 1
            left += 1
        best = max(best, right - left + 1)
    return best
""", [["ABAB", 2], ["AABABBA", 1], ["A", 0], ["AAAA", 0], ["ABCDE", 1], ["BAAAB", 2]],
        [(["ABAB", 2], 4), (["AABABBA", 1], 4)], "O(n)", ("window",)),
    Golden("minimum-window-substring", "minWindow", [("s", "str"), ("t", "str")], """
def minWindow(s, t):
    need, missing, left, best = {}, len(t), 0, (0, float("inf"))
    for c in t:
        need[c] = need.get(c, 0) + 1
    for right, c in enumerate(s):
        if need.get(c, 0) > 0:
            missing -= 1
        need[c] = need.get(c, 0) - 1
        if missing == 0:
            while need[s[left]] < 0:
                need[s[left]] += 1
                left += 1
            if right - left < best[1] - best[0]:
                best = (left, right)
            need[s[left]] += 1
            missing += 1
            left += 1
    return "" if best[1] == float("inf") else s[best[0]:best[1] + 1]
""", [["ADOBECODEBANC", "ABC"], ["a", "a"], ["a", "aa"], ["ab", "b"], ["bba", "ab"], ["aaflslflsldkalskaaa", "aaa"]],
        [(["ADOBECODEBANC", "ABC"], "BANC"), (["a", "aa"], "")], "O(n)", ("window",)),
    # ---------------------------------------------------------------- Stack
    Golden("valid-parentheses", "isValid", [("s", "str")], """
def isValid(s):
    pairs, stack = {")": "(", "]": "[", "}": "{"}, []
    for c in s:
        if c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
        else:
            stack.append(c)
    return not stack
""", [["()"], ["()[]{}"], ["(]"], ["([)]"], ["{[]}"], ["("], ["]"]],
        [(["()[]{}"], True), (["([)]"], False)], "O(n)", ("stack",)),
    # ---------------------------------------------------------------- Binary Search
    Golden("binary-search", "search", [("nums", INTS), ("target", "int")], """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""", [[[-1, 0, 3, 5, 9, 12], 9], [[-1, 0, 3, 5, 9, 12], 2], [[5], 5], [[5], -5], [[1, 3], 3]],
        [([[-1, 0, 3, 5, 9, 12], 9], 4), ([[-1, 0, 3, 5, 9, 12], 2], -1)], "O(log n)", ("binary search",)),
    Golden("find-minimum-in-rotated-sorted-array", "findMin", [("nums", INTS)], """
def findMin(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1
        else:
            hi = mid
    return nums[lo]
""", [[[3, 4, 5, 1, 2]], [[4, 5, 6, 7, 0, 1, 2]], [[11, 13, 15, 17]], [[1]], [[2, 1]]],
        [([[3, 4, 5, 1, 2]], 1), ([[11, 13, 15, 17]], 11)], "O(log n)", ("binary search",)),
    Golden("search-in-rotated-sorted-array", "search", [("nums", INTS), ("target", "int")], """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
""", [[[4, 5, 6, 7, 0, 1, 2], 0], [[4, 5, 6, 7, 0, 1, 2], 3], [[1], 0], [[1, 3], 3], [[3, 1], 1], [[5, 1, 3], 5]],
        [([[4, 5, 6, 7, 0, 1, 2], 0], 4), ([[4, 5, 6, 7, 0, 1, 2], 3], -1)], "O(log n)", ("binary search",)),
    Golden("koko-eating-bananas", "minEatingSpeed", [("piles", INTS), ("h", "int")], """
def minEatingSpeed(piles, h):
    lo, hi = 1, max(piles)
    while lo < hi:
        k = (lo + hi) // 2
        if sum((p + k - 1) // k for p in piles) <= h:
            hi = k
        else:
            lo = k + 1
    return lo
""", [[[3, 6, 7, 11], 8], [[30, 11, 23, 4, 20], 5], [[30, 11, 23, 4, 20], 6], [[312884470], 312884469], [[1000000000], 2]],
        [([[3, 6, 7, 11], 8], 4), ([[30, 11, 23, 4, 20], 6], 23)], "O(n log m)", ("binary search",)),
    # ---------------------------------------------------------------- Linked List
    Golden("reverse-linked-list", "reverseList", [("head", L)], """
def reverseList(head):
    prev = None
    while head:
        head.next, prev, head = prev, head, head.next
    return prev
""", [[[1, 2, 3, 4, 5]], [[1, 2]], [[]], [[7]]],
        [([[1, 2, 3, 4, 5]], [5, 4, 3, 2, 1]), ([[]], [])], "O(n)", ("pointer", "linked list", "iterat", "revers"), return_type=L),
    Golden("merge-two-sorted-lists", "mergeTwoLists", [("list1", L), ("list2", L)], """
def mergeTwoLists(list1, list2):
    dummy = tail = ListNode()
    while list1 and list2:
        if list1.val <= list2.val:
            tail.next, list1 = list1, list1.next
        else:
            tail.next, list2 = list2, list2.next
        tail = tail.next
    tail.next = list1 or list2
    return dummy.next
""", [[[1, 2, 4], [1, 3, 4]], [[], []], [[], [0]], [[5], [1, 2, 4]], [[-3, -1], [-2, 0, 9]]],
        [([[1, 2, 4], [1, 3, 4]], [1, 1, 2, 3, 4, 4])], "O(n + m)", ("pointer", "merge", "linked list"), return_type=L),
    Golden("remove-nth-node-from-end-of-list", "removeNthFromEnd", [("head", L), ("n", "int")], """
def removeNthFromEnd(head, n):
    dummy = ListNode(0, head)
    fast = slow = dummy
    for _ in range(n):
        fast = fast.next
    while fast.next:
        fast, slow = fast.next, slow.next
    slow.next = slow.next.next
    return dummy.next
""", [[[1, 2, 3, 4, 5], 2], [[1], 1], [[1, 2], 1], [[1, 2], 2], [[1, 2, 3], 3]],
        [([[1, 2, 3, 4, 5], 2], [1, 2, 3, 5]), ([[1], 1], [])], "O(n)", ("two pointer", "fast", "gap"), return_type=L),
    Golden("reorder-list", "reorderList", [("head", L)], """
def reorderList(head):
    nodes = []
    while head:
        nodes.append(head)
        head = head.next
    i, j = 0, len(nodes) - 1
    while i < j:
        nodes[i].next = nodes[j]
        i += 1
        if i == j:
            break
        nodes[j].next = nodes[i]
        j -= 1
    if nodes:
        nodes[i].next = None
""", [[[1, 2, 3, 4]], [[1, 2, 3, 4, 5]], [[1]], [[1, 2]]],
        [([[1, 2, 3, 4]], [1, 4, 2, 3]), ([[1, 2, 3, 4, 5]], [1, 5, 2, 4, 3])], "O(n)",
        ("pointer", "revers", "middle", "fast"), in_place_arg=0),
    # ---------------------------------------------------------------- Trees
    Golden("invert-binary-tree", "invertTree", [("root", T)], """
def invertTree(root):
    if root:
        root.left, root.right = invertTree(root.right), invertTree(root.left)
    return root
""", [[[4, 2, 7, 1, 3, 6, 9]], [[2, 1, 3]], [[]], [[1, 2]], [[1, None, 2]]],
        [([[4, 2, 7, 1, 3, 6, 9]], [4, 7, 2, 9, 6, 3, 1])], "O(n)", ("recurs", "dfs", "depth", "tree", "traversal"), return_type=T),
    Golden("maximum-depth-of-binary-tree", "maxDepth", [("root", T)], """
def maxDepth(root):
    return 0 if not root else 1 + max(maxDepth(root.left), maxDepth(root.right))
""", [[[3, 9, 20, None, None, 15, 7]], [[1, None, 2]], [[]], [[1, 2, 3, 4, None, None, 5, 6]]],
        [([[3, 9, 20, None, None, 15, 7]], 3), ([[]], 0)], "O(n)", ("recurs", "dfs", "depth", "bfs")),
    Golden("same-tree", "isSameTree", [("p", T), ("q", T)], """
def isSameTree(p, q):
    if not p or not q:
        return p is q
    return p.val == q.val and isSameTree(p.left, q.left) and isSameTree(p.right, q.right)
""", [[[1, 2, 3], [1, 2, 3]], [[1, 2], [1, None, 2]], [[1, 2, 1], [1, 1, 2]], [[], []], [[1], []]],
        [([[1, 2, 3], [1, 2, 3]], True), ([[1, 2], [1, None, 2]], False)], "O(n)", ("recurs", "dfs", "depth", "traversal")),
    Golden("validate-binary-search-tree", "isValidBST", [("root", T)], """
def isValidBST(root, lo=float("-inf"), hi=float("inf")):
    if not root:
        return True
    return lo < root.val < hi and isValidBST(root.left, lo, root.val) and isValidBST(root.right, root.val, hi)
""", [[[2, 1, 3]], [[5, 1, 4, None, None, 3, 6]], [[2, 2, 2]], [[5, 4, 6, None, None, 3, 7]], [[1]], [[-2147483648, None, 2147483647]]],
        [([[2, 1, 3]], True), ([[5, 1, 4, None, None, 3, 6]], False)], "O(n)", ("recurs", "dfs", "bound", "range", "inorder")),
    Golden("kth-smallest-element-in-a-bst", "kthSmallest", [("root", T), ("k", "int")], """
def kthSmallest(root, k):
    stack = []
    while True:
        while root:
            stack.append(root)
            root = root.left
        root = stack.pop()
        k -= 1
        if k == 0:
            return root.val
        root = root.right
""", [[[3, 1, 4, None, 2], 1], [[5, 3, 6, 2, 4, None, None, 1], 3], [[1], 1], [[2, 1, 3], 3]],
        [([[3, 1, 4, None, 2], 1], 1), ([[5, 3, 6, 2, 4, None, None, 1], 3], 3)], "O(h + k)", ("inorder", "in-order", "traversal", "dfs")),
    Golden("binary-tree-level-order-traversal", "levelOrder", [("root", T)], """
def levelOrder(root):
    out, level = [], [root] if root else []
    while level:
        out.append([n.val for n in level])
        level = [c for n in level for c in (n.left, n.right) if c]
    return out
""", [[[3, 9, 20, None, None, 15, 7]], [[1]], [[]], [[1, 2, 3, 4, None, None, 5]]],
        [([[3, 9, 20, None, None, 15, 7]], [[3], [9, 20], [15, 7]])], "O(n)", ("bfs", "breadth", "level", "queue")),
    # ---------------------------------------------------------------- Heap
    Golden("top-k-frequent-elements", "topKFrequent", [("nums", INTS), ("k", "int")], """
def topKFrequent(nums, k):
    count = {}
    for x in nums:
        count[x] = count.get(x, 0) + 1
    return sorted(count, key=lambda x: -count[x])[:k]
""", [[[1, 1, 1, 2, 2, 3], 2], [[1], 1], [[4, 4, 4, 5, 5, 6, 6, 6, 6], 1], [[-1, -1, 2, 2, 3], 2]],
        [([[1, 1, 1, 2, 2, 3], 2], [1, 2])], "O(n)", ("heap", "bucket", "count", "frequen"), comparison="unordered"),
    # ---------------------------------------------------------------- Graphs
    Golden("number-of-islands", "numIslands", [("grid", "List[List[str]]")], """
def numIslands(grid):
    rows, cols, count = len(grid), len(grid[0]), 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1":
                count += 1
                stack = [(r, c)]
                grid[r][c] = "0"
                while stack:
                    i, j = stack.pop()
                    for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                        if 0 <= a < rows and 0 <= b < cols and grid[a][b] == "1":
                            grid[a][b] = "0"
                            stack.append((a, b))
    return count
""", [[[["1", "1", "0", "0"], ["1", "1", "0", "0"], ["0", "0", "1", "0"], ["0", "0", "0", "1"]]], [[["0"]]], [[["1"]]],
      [[["1", "0", "1"], ["0", "1", "0"], ["1", "0", "1"]]], [[["1", "1", "1"], ["0", "1", "0"], ["1", "1", "1"]]]],
        [([[["1", "1", "0", "0"], ["1", "1", "0", "0"], ["0", "0", "1", "0"], ["0", "0", "0", "1"]]], 3)],
        "O(m n)", ("dfs", "bfs", "flood", "graph", "union")),
    Golden("course-schedule", "canFinish", [("numCourses", "int"), ("prerequisites", "List[List[int]]")], """
def canFinish(numCourses, prerequisites):
    indeg, adj = [0] * numCourses, [[] for _ in range(numCourses)]
    for a, b in prerequisites:
        adj[b].append(a)
        indeg[a] += 1
    ready = [i for i in range(numCourses) if indeg[i] == 0]
    done = 0
    while ready:
        n = ready.pop()
        done += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
    return done == numCourses
""", [[2, [[1, 0]]], [2, [[1, 0], [0, 1]]], [1, []], [3, [[1, 0], [2, 1]]], [4, [[1, 0], [2, 1], [3, 2], [1, 3]]]],
        [([2, [[1, 0]]], True), ([2, [[1, 0], [0, 1]]], False)], "O(V + E)", ("topolog", "cycle", "dfs", "kahn", "graph")),
    # ---------------------------------------------------------------- 1-D DP
    Golden("climbing-stairs", "climbStairs", [("n", "int")], """
def climbStairs(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a
""", [[1], [2], [3], [5], [45]], [([2], 2), ([3], 3)], "O(n)", ("dynamic", "dp", "fibonacci")),
    Golden("house-robber", "rob", [("nums", INTS)], """
def rob(nums):
    take, skip = 0, 0
    for x in nums:
        take, skip = skip + x, max(take, skip)
    return max(take, skip)
""", [[[1, 2, 3, 1]], [[2, 7, 9, 3, 1]], [[0]], [[2, 1, 1, 2]], [[5, 5, 10, 100, 10, 5]]],
        [([[1, 2, 3, 1]], 4), ([[2, 7, 9, 3, 1]], 12)], "O(n)", ("dynamic", "dp")),
    Golden("coin-change", "coinChange", [("coins", INTS), ("amount", "int")], """
def coinChange(coins, amount):
    INF = amount + 1
    best = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                best[a] = min(best[a], best[a - c] + 1)
    return -1 if best[amount] == INF else best[amount]
""", [[[1, 2, 5], 11], [[2], 3], [[1], 0], [[186, 419, 83, 408], 6249], [[2, 5, 10, 1], 27]],
        [([[1, 2, 5], 11], 3), ([[2], 3], -1)], "O(amount * n)", ("dynamic", "dp")),
    Golden("longest-increasing-subsequence", "lengthOfLIS", [("nums", INTS)], """
def lengthOfLIS(nums):
    import bisect
    tails = []
    for x in nums:
        i = bisect.bisect_left(tails, x)
        tails[i:i + 1] = [x]
    return len(tails)
""", [[[10, 9, 2, 5, 3, 7, 101, 18]], [[0, 1, 0, 3, 2, 3]], [[7, 7, 7, 7]], [[1]], [[4, 10, 4, 3, 8, 9]]],
        [([[10, 9, 2, 5, 3, 7, 101, 18]], 4), ([[7, 7, 7, 7]], 1)], "O(n log n)", ("dynamic", "dp", "binary search", "patience")),
    Golden("word-break", "wordBreak", [("s", "str"), ("wordDict", "List[str]")], """
def wordBreak(s, wordDict):
    words, ok = set(wordDict), [True] + [False] * len(s)
    for i in range(1, len(s) + 1):
        ok[i] = any(ok[j] and s[j:i] in words for j in range(i))
    return ok[-1]
""", [["leetcode", ["leet", "code"]], ["applepenapple", ["apple", "pen"]], ["catsandog", ["cats", "dog", "sand", "and", "cat"]],
      ["a", ["b"]], ["aaaaaaa", ["aaaa", "aaa"]]],
        [(["leetcode", ["leet", "code"]], True), (["catsandog", ["cats", "dog", "sand", "and", "cat"]], False)],
        "O(n^2)", ("dynamic", "dp")),
    # ---------------------------------------------------------------- 2-D DP
    Golden("unique-paths", "uniquePaths", [("m", "int"), ("n", "int")], """
def uniquePaths(m, n):
    row = [1] * n
    for _ in range(1, m):
        for j in range(1, n):
            row[j] += row[j - 1]
    return row[-1]
""", [[3, 7], [3, 2], [1, 1], [10, 10], [1, 5]], [([3, 7], 28), ([3, 2], 3)], "O(m n)", ("dynamic", "dp", "combinat")),
    Golden("longest-common-subsequence", "longestCommonSubsequence", [("text1", "str"), ("text2", "str")], """
def longestCommonSubsequence(text1, text2):
    prev = [0] * (len(text2) + 1)
    for a in text1:
        cur = [0]
        for j, b in enumerate(text2):
            cur.append(prev[j] + 1 if a == b else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]
""", [["abcde", "ace"], ["abc", "abc"], ["abc", "def"], ["bsbininm", "jmjkbkjkv"], ["a", "a"]],
        [(["abcde", "ace"], 3), (["abc", "def"], 0)], "O(m n)", ("dynamic", "dp")),
    # ---------------------------------------------------------------- Greedy
    Golden("maximum-subarray", "maxSubArray", [("nums", INTS)], """
def maxSubArray(nums):
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
""", [[[-2, 1, -3, 4, -1, 2, 1, -5, 4]], [[1]], [[5, 4, -1, 7, 8]], [[-3, -2, -5]], [[0, -1]]],
        [([[-2, 1, -3, 4, -1, 2, 1, -5, 4]], 6), ([[-3, -2, -5]], -2)], "O(n)", ("kadane", "dynamic", "dp", "greedy")),
    Golden("jump-game", "canJump", [("nums", INTS)], """
def canJump(nums):
    reach = 0
    for i, x in enumerate(nums):
        if i > reach:
            return False
        reach = max(reach, i + x)
    return True
""", [[[2, 3, 1, 1, 4]], [[3, 2, 1, 0, 4]], [[0]], [[2, 0, 0]], [[1, 0, 1]]],
        [([[2, 3, 1, 1, 4]], True), ([[3, 2, 1, 0, 4]], False)], "O(n)", ("greedy",)),
    # ---------------------------------------------------------------- Intervals
    Golden("insert-interval", "insert", [("intervals", "List[List[int]]"), ("newInterval", INTS)], """
def insert(intervals, newInterval):
    out, (s, e), placed = [], newInterval, False
    for a, b in intervals:
        if b < s:
            out.append([a, b])
        elif a > e:
            if not placed:
                out.append([s, e])
                placed = True
            out.append([a, b])
        else:
            s, e = min(s, a), max(e, b)
    if not placed:
        out.append([s, e])
    return out
""", [[[[1, 3], [6, 9]], [2, 5]], [[[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], [4, 8]], [[], [5, 7]], [[[1, 5]], [2, 3]],
      [[[1, 5]], [6, 8]], [[[3, 5]], [1, 2]]],
        [([[[1, 3], [6, 9]], [2, 5]], [[1, 5], [6, 9]])], "O(n)", ("interval", "merge", "sweep", "linear")),
    Golden("non-overlapping-intervals", "eraseOverlapIntervals", [("intervals", "List[List[int]]")], """
def eraseOverlapIntervals(intervals):
    end, kept = float("-inf"), 0
    for a, b in sorted(intervals, key=lambda x: x[1]):
        if a >= end:
            kept += 1
            end = b
    return len(intervals) - kept
""", [[[[1, 2], [2, 3], [3, 4], [1, 3]]], [[[1, 2], [1, 2], [1, 2]]], [[[1, 2], [2, 3]]], [[[1, 100], [11, 22], [1, 11], [2, 12]]]],
        [([[[1, 2], [2, 3], [3, 4], [1, 3]]], 1), ([[[1, 2], [1, 2], [1, 2]]], 2)], "O(n log n)", ("greedy", "sort", "interval")),
    # ---------------------------------------------------------------- Math & Geometry
    Golden("rotate-image", "rotate", [("matrix", "List[List[int]]")], """
def rotate(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    for row in matrix:
        row.reverse()
""", [[[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], [[[5, 1, 9, 11], [2, 4, 8, 10], [13, 3, 6, 7], [15, 14, 12, 16]]], [[[1]]], [[[1, 2], [3, 4]]]],
        [([[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], [[7, 4, 1], [8, 5, 2], [9, 6, 3]])], "O(n^2)",
        ("transpose", "layer", "rotat", "matrix"), in_place_arg=0),
    Golden("spiral-matrix", "spiralOrder", [("matrix", "List[List[int]]")], """
def spiralOrder(matrix):
    out = []
    while matrix:
        out += matrix.pop(0)
        matrix = [list(r) for r in zip(*matrix)][::-1]
    return out
""", [[[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], [[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]], [[[1]]], [[[1], [2], [3]]], [[[1, 2, 3]]]],
        [([[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], [1, 2, 3, 6, 9, 8, 7, 4, 5])], "O(m n)", ("boundar", "simulat", "layer", "spiral", "matrix")),
    # ---------------------------------------------------------------- Bit Manipulation
    Golden("number-of-1-bits", "hammingWeight", [("n", "int")], """
def hammingWeight(n):
    return bin(n).count("1")
""", [[11], [128], [2147483645], [1]], [([11], 3), ([128], 1)], "O(1)", ("bit",)),
    Golden("counting-bits", "countBits", [("n", "int")], """
def countBits(n):
    out = [0] * (n + 1)
    for i in range(1, n + 1):
        out[i] = out[i >> 1] + (i & 1)
    return out
""", [[2], [5], [0], [16]], [([2], [0, 1, 1]), ([5], [0, 1, 1, 2, 1, 2])], "O(n)", ("bit", "dynamic", "dp")),
    Golden("missing-number", "missingNumber", [("nums", INTS)], """
def missingNumber(nums):
    return len(nums) * (len(nums) + 1) // 2 - sum(nums)
""", [[[3, 0, 1]], [[0, 1]], [[9, 6, 4, 2, 3, 5, 7, 0, 1]], [[0]], [[1]]],
        [([[3, 0, 1]], 2), ([[9, 6, 4, 2, 3, 5, 7, 0, 1]], 8)], "O(n)", ("bit", "xor", "sum", "math", "gauss")),
    # ---------------------------------------------------------------- Special structures
    Golden("clone-graph", "cloneGraph", [("node", "Optional[GraphNode]")], """
def cloneGraph(node):
    if not node:
        return None
    copies = {node: Node(node.val)}
    stack = [node]
    while stack:
        n = stack.pop()
        for m in n.neighbors:
            if m not in copies:
                copies[m] = Node(m.val)
                stack.append(m)
            copies[n].neighbors.append(copies[m])
    return copies[node]
""", [[[[2, 4], [1, 3], [2, 4], [1, 3]]], [[[]]], [[]], [[[2], [1]]], [[[2, 3], [1, 3], [1, 2]]]],
        [([[[2, 4], [1, 3], [2, 4], [1, 3]]], [[2, 4], [1, 3], [2, 4], [1, 3]]), ([[]], [])],
        "O(V + E)", ("dfs", "bfs", "hash", "graph", "clone"), return_type="Optional[GraphNode]"),
    Golden("copy-list-with-random-pointer", "copyRandomList", [("head", "Optional[RandomNode]")], """
def copyRandomList(head):
    copies, n = {None: None}, head
    while n:
        copies[n] = Node(n.val)
        n = n.next
    n = head
    while n:
        copies[n].next, copies[n].random = copies[n.next], copies[n.random]
        n = n.next
    return copies[head]
""", [[[[7, None], [13, 0], [11, 4], [10, 2], [1, 0]]], [[[1, 1], [2, 1]]], [[[3, None], [3, 0], [3, None]]], [[]]],
        [([[[1, 1], [2, 1]]], [[1, 1], [2, 1]])], "O(n)", ("hash", "interleav", "weav", "map", "copy"),
        return_type="Optional[RandomNode]"),
    Golden("linked-list-cycle", "hasCycle", [("head", L)], """
def hasCycle(head):
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow is fast:
            return True
    return False
""", [[{"values": [3, 2, 0, -4], "pos": 1}], [{"values": [1, 2], "pos": 0}], [{"values": [1], "pos": -1}],
      [{"values": [], "pos": -1}], [{"values": [1, 2, 3, 4, 5], "pos": 4}]],
        [([{"values": [3, 2, 0, -4], "pos": 1}], True), ([{"values": [1], "pos": -1}], False)],
        "O(n)", ("fast", "slow", "floyd", "tortoise", "two pointer")),
    Golden("lowest-common-ancestor-of-a-binary-search-tree", "lowestCommonAncestor",
           [("root", "TreeNode"), ("p", "TreeNode"), ("q", "TreeNode")], """
def lowestCommonAncestor(root, p, q):
    while root:
        if p.val < root.val and q.val < root.val:
            root = root.left
        elif p.val > root.val and q.val > root.val:
            root = root.right
        else:
            return root
""", [[[6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], 2, 8], [[6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], 2, 4],
      [[2, 1], 2, 1], [[6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], 3, 5], [[6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], 0, 9]],
        [([[2, 1], 2, 1], [2, 1])], "O(h)", ("bst", "binary search tree", "split", "ordering", "compare"),
        return_type="TreeNode"),
    Golden("serialize-and-deserialize-binary-tree", "Codec", [("root", T)], """
class Codec:
    def serialize(self, root):
        return json.dumps(tree_values(root))

    def deserialize(self, data):
        return tree_from(json.loads(data))


import json


def tree_values(root):
    out, queue = [], collections.deque([root])
    while queue:
        n = queue.popleft()
        out.append(n.val if n else None)
        if n:
            queue += [n.left, n.right]
    while out and out[-1] is None:
        out.pop()
    return out


def tree_from(vals):
    if not vals:
        return None
    root = TreeNode(vals[0])
    queue, i = collections.deque([root]), 1
    while queue and i < len(vals):
        n = queue.popleft()
        for side in ("left", "right"):
            if i < len(vals) and vals[i] is not None:
                setattr(n, side, TreeNode(vals[i]))
                queue.append(getattr(n, side))
            i += 1
    return root
""", [[[1, 2, 3, None, None, 4, 5]], [[]], [[1]], [[-1, None, -2, None, -3]], [[5, 4, 7, 3, None, 2, None, -1, None, 9]]],
        [([[1, 2, 3, None, None, 4, 5]], [1, 2, 3, None, None, 4, 5])], "O(n)",
        ("bfs", "dfs", "preorder", "level", "serializ", "traversal"), return_type=T, kind="codec"),
    Golden("encode-and-decode-strings", "Codec", [("strs", "List[str]")], """
class Codec:
    def encode(self, strs):
        return "".join(f"{len(s)}#{s}" for s in strs)

    def decode(self, s):
        out, i = [], 0
        while i < len(s):
            j = s.index("#", i)
            n = int(s[i:j])
            out.append(s[j + 1:j + 1 + n])
            i = j + 1 + n
        return out
""", [[["lint", "code", "love", "you"]], [[""]], [[]], [["#", "12#ab", ""]], [["a,b", "c;d", "\\n"]]],
        [([["we", "say", ":", "yes"]], ["we", "say", ":", "yes"])], "O(n)",
        ("length", "prefix", "delimit", "escap", "encod"), return_type="List[str]", kind="codec"),
    # ---------------------------------------------------------------- Design
    Golden("lru-cache", "LRUCache", [("operations", "List[str]"), ("arguments", "List[List]")], """
class LRUCache:
    def __init__(self, capacity):
        self.capacity, self.data = capacity, OrderedDict()

    def get(self, key):
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key, value):
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
""", [[["LRUCache", "put", "put", "get", "put", "get", "put", "get", "get", "get"],
       [[2], [1, 1], [2, 2], [1], [3, 3], [2], [4, 4], [1], [3], [4]]],
      [["LRUCache", "put", "get", "put", "get", "get"], [[1], [2, 1], [2], [3, 2], [2], [3]]],
      [["LRUCache", "put", "put", "put", "get", "get"], [[2], [1, 1], [1, 5], [2, 2], [1], [2]]],
      [["LRUCache", "put", "put", "get", "put", "get", "get"], [[2], [1, 1], [2, 2], [1], [3, 3], [2], [1]]]],
        [([["LRUCache", "put", "get", "put", "get", "get"], [[1], [2, 1], [2], [3, 2], [2], [3]]], [None, None, 1, None, -1, 2])],
        "O(1)", ("hash", "linked list", "ordered"), kind="design"),
    Golden("min-stack", "MinStack", [("operations", "List[str]"), ("arguments", "List[List]")], """
class MinStack:
    def __init__(self):
        self.stack = []

    def push(self, val):
        self.stack.append((val, min(val, self.stack[-1][1]) if self.stack else val))

    def pop(self):
        self.stack.pop()

    def top(self):
        return self.stack[-1][0]

    def getMin(self):
        return self.stack[-1][1]
""", [[["MinStack", "push", "push", "push", "getMin", "pop", "top", "getMin"], [[], [-2], [0], [-3], [], [], [], []]],
      [["MinStack", "push", "push", "getMin", "pop", "getMin"], [[], [1], [1], [], [], []]],
      [["MinStack", "push", "getMin", "top", "push", "getMin"], [[], [5], [], [], [3], []]]],
        [([["MinStack", "push", "push", "push", "getMin", "pop", "top", "getMin"], [[], [-2], [0], [-3], [], [], [], []]],
          [None, None, None, None, -3, None, 0, -2])],
        "O(1)", ("stack",), kind="design"),
]

BY_ID = {g.id: g for g in GOLDEN}
