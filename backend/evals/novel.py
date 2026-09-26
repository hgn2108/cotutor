"""Novel problems: original wording and twists, so the models can't just recall a famous answer.

The famous-problem set measures a best case (models have seen those problems many times). These
are written for Cotutor, reach the pipeline as pasted statements (no names, no signature check)
and cover the weak spots: statements with no examples, multiple valid answers, design classes,
linked lists and trees.
"""

from __future__ import annotations

from .golden import Golden

INTS = "List[int]"
GRID = "List[List[int]]"

NOVEL: list[Golden] = [
    Golden("novel-equal-step-run", "longest_equal_step_run", [("nums", INTS)], """
def longest_equal_step_run(nums):
    if len(nums) < 3:
        return len(nums)
    best = cur = 2
    for i in range(2, len(nums)):
        cur = cur + 1 if nums[i] - nums[i - 1] == nums[i - 1] - nums[i - 2] else 2
        best = max(best, cur)
    return best
""", [[[1, 3, 5, 7, 2, 1]], [[]], [[5]], [[1, 2]], [[4, 4, 4, 1, -2, -5]], [[1, 2, 4, 7, 11]], [[10, 7, 4, 1, -2, 0, 2, 4]]],
        [([[1, 3, 5, 7, 2, 1]], 4), ([[4, 4, 4, 1, -2, -5]], 4), ([[]], 0), ([[5]], 1)],
        "O(n)", ("scan", "one pass", "window", "linear", "run", "track"), statement="""
Implement `def longest_equal_step_run(nums: List[int]) -> int`.

A "steady stretch" is a contiguous part of the list where every two neighbours differ by the same
amount. Return the length of the longest steady stretch. A single number counts as a stretch of
length 1, and an empty list gives 0.

Example: nums = [1, 3, 5, 7, 2, 1] -> 4 (the stretch 1, 3, 5, 7 steps by 2)
Example: nums = [5] -> 1
"""),
    Golden("novel-earliest-full-house", "earliest_full_house", [("events", GRID), ("k", "int"), ("w", "int")], """
def earliest_full_house(events, k, w):
    window, count = collections.deque(), {}
    for t, p in events:
        window.append((t, p))
        count[p] = count.get(p, 0) + 1
        while window and window[0][0] <= t - w:
            _, old = window.popleft()
            count[old] -= 1
            if count[old] == 0:
                del count[old]
        if len(count) >= k:
            return t
    return -1
""", [[[[1, 1], [2, 2], [4, 1], [5, 3]], 3, 5], [[[1, 1], [2, 2], [4, 1], [5, 3]], 3, 3], [[], 1, 10], [[[3, 7]], 1, 1],
      [[[1, 1], [1, 2], [1, 3]], 3, 1], [[[1, 1], [2, 1], [3, 1]], 2, 10], [[[1, 1], [10, 2], [11, 3], [12, 1]], 3, 3]],
        [([[[1, 1], [2, 2], [4, 1], [5, 3]], 3, 5], 5), ([[[1, 1], [2, 2], [4, 1], [5, 3]], 3, 3], -1),
         ([[[1, 1], [10, 2], [11, 3], [12, 1]], 3, 3], 12)],
        "O(n)", ("window", "sliding", "queue", "deque"), statement="""
Implement `def earliest_full_house(events: List[List[int]], k: int, w: int) -> int`.

An office logs badge scans as events [time, person_id], sorted by time. Return the earliest scan
time t at which at least k different people have scanned during the last w minutes, meaning the
window (t - w, t]. If that never happens, return -1.

Example: events = [[1,1],[2,2],[4,1],[5,3]], k = 3, w = 5 -> 5
Example: events = [[1,1],[2,2],[4,1],[5,3]], k = 3, w = 3 -> -1
"""),
    Golden("novel-rooms-with-cleanup", "rooms_with_cleanup", [("meetings", GRID), ("cleanup", "int")], """
def rooms_with_cleanup(meetings, cleanup):
    ready = []
    for start, end in sorted(meetings):
        if ready and ready[0] <= start:
            heapq.heappop(ready)
        heapq.heappush(ready, end + cleanup)
    return len(ready)
""", [[[[0, 30], [5, 10], [15, 20]], 0], [[[0, 30], [5, 10], [15, 20]], 5], [[[0, 10], [12, 20]], 3], [[[0, 10], [12, 20]], 2],
      [[], 4], [[[1, 2]], 0], [[[1, 5], [2, 6], [3, 7], [5, 8]], 0]],
        [([[[0, 10], [12, 20]], 3], 2), ([[[0, 10], [12, 20]], 2], 1), ([[[1, 5], [2, 6], [3, 7], [5, 8]], 0], 3)],
        "O(n log n)", ("heap", "priority", "sweep", "sort"), statement="""
Implement `def rooms_with_cleanup(meetings: List[List[int]], cleanup: int) -> int`.

Each meeting [start, end) needs a room. After a meeting ends, its room must be cleaned for
`cleanup` minutes before the next meeting can use it (a meeting may start at the exact minute the
room becomes ready). Return the minimum number of rooms needed.

Example: meetings = [[0,10],[12,20]], cleanup = 3 -> 2
Example: meetings = [[0,10],[12,20]], cleanup = 2 -> 1
"""),
    Golden("novel-cheapest-path-one-free", "cheapest_path_one_free", [("grid", GRID)], """
def cheapest_path_one_free(grid):
    rows, cols, inf = len(grid), len(grid[0]), float("inf")
    paid = [[inf] * cols for _ in range(rows)]
    free = [[inf] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if r == 0 and c == 0:
                paid[0][0], free[0][0] = grid[0][0], 0
                continue
            best_paid = min(paid[r - 1][c] if r else inf, paid[r][c - 1] if c else inf)
            best_free = min(free[r - 1][c] if r else inf, free[r][c - 1] if c else inf)
            paid[r][c] = best_paid + grid[r][c]
            free[r][c] = min(best_free + grid[r][c], best_paid)
    return min(paid[-1][-1], free[-1][-1])
""", [[[[1, 3, 1], [1, 5, 1], [4, 2, 1]]], [[[5]]], [[[1, 2, 3]]], [[[0, 0], [0, 0]]], [[[9, 1], [1, 9]]], [[[2], [7], [1]]]],
        [([[[1, 3, 1], [1, 5, 1], [4, 2, 1]]], 4), ([[[5]]], 0), ([[[1, 2, 3]]], 3), ([[[9, 1], [1, 9]]], 10)],
        "O(m n)", ("dynamic", "dp"), statement="""
Implement `def cheapest_path_one_free(grid: List[List[int]]) -> int`.

You walk from the top-left cell to the bottom-right cell of a grid of non-negative costs, moving
only right or down, and you pay the cost of every cell you stand on (including the first and
last). You hold one voucher that lets you skip paying for a single cell of your choice. Return the
minimum total you have to pay.

Example: grid = [[1,3,1],[1,5,1],[4,2,1]] -> 4
Example: grid = [[5]] -> 0
"""),
    Golden("novel-palindrome-fill-count", "palindrome_fill_count", [("s", "str")], """
def palindrome_fill_count(s):
    mod, ways, i, j = 1_000_000_007, 1, 0, len(s) - 1
    while i < j:
        a, b = s[i], s[j]
        if a == "?" and b == "?":
            ways = ways * 26 % mod
        elif a != "?" and b != "?" and a != b:
            return 0
        i, j = i + 1, j - 1
    if i == j and s[i] == "?":
        ways = ways * 26 % mod
    return ways
""", [["a?"], ["??"], ["ab"], ["?"], ["a?c"], ["a??a"], ["?????"], [""]],
        [(["a?"], 1), (["??"], 26), (["ab"], 0), (["a?c"], 0), (["a??a"], 26), (["?????"], 17576), ([""], 1)],
        "O(n)", ("two pointer", "pair", "count", "combinat", "mirror"), statement="""
Implement `def palindrome_fill_count(s: str) -> int`.

s contains lowercase letters and question marks. Every question mark must be replaced by a
lowercase letter. Count the number of ways to do this so that the result reads the same forwards
and backwards. Return the count modulo 1_000_000_007.

Example: s = "a?" -> 1
Example: s = "??" -> 26
"""),
    Golden("novel-longest-append-chain", "longest_append_chain", [("words", "List[str]")], """
def longest_append_chain(words):
    best, chain = 0, {}
    for w in sorted(set(words), key=len):
        chain[w] = chain.get(w[:-1], 0) + 1
        best = max(best, chain[w])
    return best
""", [[["a", "ab", "abc", "b", "abd"]], [["x"]], [[]], [["ab", "abc"]], [["a", "ba", "bca"]], [["dog", "do", "d", "dogs", "cat"]]],
        [([["a", "ab", "abc", "b", "abd"]], 3), ([["ab", "abc"]], 2), ([["a", "ba", "bca"]], 1), ([["dog", "do", "d", "dogs", "cat"]], 4)],
        "O(n L)", ("dynamic", "dp", "hash"), statement="""
Implement `def longest_append_chain(words: List[str]) -> int`.

A word may follow another word in a chain if it is exactly the previous word with one letter
added at the end ("ca" can be followed by "cat", but not by "act" or "bca"). Using each word from
the list at most once, return the length of the longest chain. An empty list gives 0.

Example: words = ["a","ab","abc","b","abd"] -> 3
"""),
    Golden("novel-min-days-all-tasks", "min_days_all_tasks", [("n", "int"), ("deps", GRID)], """
def min_days_all_tasks(n, deps):
    indeg, adj = [0] * n, [[] for _ in range(n)]
    for a, b in deps:
        adj[a].append(b)
        indeg[b] += 1
    level = [i for i in range(n) if indeg[i] == 0]
    days, done = 0, 0
    while level:
        days, done = days + 1, done + len(level)
        nxt = []
        for a in level:
            for b in adj[a]:
                indeg[b] -= 1
                if indeg[b] == 0:
                    nxt.append(b)
        level = nxt
    return days if done == n else -1
""", [[3, [[0, 1], [1, 2]]], [3, []], [2, [[0, 1], [1, 0]]], [4, [[0, 2], [1, 2], [2, 3]]], [1, []], [5, [[0, 1], [0, 2], [1, 3], [2, 3], [3, 4], [0, 4]]]],
        [([3, [[0, 1], [1, 2]]], 3), ([3, []], 1), ([2, [[0, 1], [1, 0]]], -1), ([4, [[0, 2], [1, 2], [2, 3]]], 3)],
        "O(V + E)", ("topolog", "bfs", "kahn", "graph", "level"), statement="""
Implement `def min_days_all_tasks(n: int, deps: List[List[int]]) -> int`.

There are n tasks numbered 0 to n-1 and each takes exactly one day. A dependency [a, b] means task
b can only start after task a is finished. With as many workers as you like, return the minimum
number of days needed to finish every task, or -1 if the dependencies make that impossible.

Example: n = 3, deps = [[0,1],[1,2]] -> 3
Example: n = 2, deps = [[0,1],[1,0]] -> -1
"""),
    Golden("novel-split-equal-blocks", "split_equal_blocks", [("nums", INTS), ("k", "int")], """
def split_equal_blocks(nums, k):
    total = sum(nums)
    if k <= 0 or k > len(nums) or total % k:
        return False
    target, run, blocks = total // k, 0, 0
    for x in nums:
        run += x
        if run == target:
            blocks, run = blocks + 1, 0
        elif run > target:
            return False
    return blocks == k
""", [[[2, 2, 1, 3, 4], 3], [[1, 1, 1], 4], [[5], 1], [[1, 2, 3, 3, 3], 3], [[3, 3, 3, 3], 2], [[1, 1, 2], 2], [[4, 1, 3], 2]],
        [([[2, 2, 1, 3, 4], 3], True), ([[1, 1, 1], 4], False), ([[1, 2, 3, 3, 3], 3], False), ([[4, 1, 3], 2], True)],
        "O(n)", ("prefix", "greedy", "scan", "sum", "running"), statement="""
Implement `def split_equal_blocks(nums: List[int], k: int) -> bool`.

nums holds positive integers. Decide whether nums can be cut into exactly k non-empty contiguous
blocks whose sums are all equal.

Example: nums = [2,2,1,3,4], k = 3 -> True ([2,2], [1,3], [4])
Example: nums = [1,1,1], k = 4 -> False
"""),
    Golden("novel-best-cross", "best_cross", [("grid", GRID)], """
def best_cross(grid):
    rows = [sum(r) for r in grid]
    cols = [sum(c) for c in zip(*grid)]
    return max(rows[i] + cols[j] - grid[i][j] for i in range(len(grid)) for j in range(len(grid[0])))
""", [[[[1, 2], [3, 4]]], [[[5]]], [[[-1, -2], [-3, -4]]], [[[1, 1, 1], [1, 9, 1], [1, 1, 1]]], [[[0, -5, 2]]]],
        [([[[1, 2], [3, 4]]], 9), ([[[5]]], 5), ([[[-1, -2], [-3, -4]]], -6), ([[[1, 1, 1], [1, 9, 1], [1, 1, 1]]], 13)],
        "O(m n)", ("prefix", "precomput", "sum", "matrix", "row"), statement="""
Implement `def best_cross(grid: List[List[int]]) -> int`.

Pick one row and one column of the grid. Their score is the sum of every cell in the row plus
every cell in the column, with the cell where they cross counted only once. Values can be
negative. Return the highest possible score.

Example: grid = [[1,2],[3,4]] -> 9
"""),
    Golden("novel-max-fair-pairs", "max_fair_pairs", [("skills", INTS), ("d", "int")], """
def max_fair_pairs(skills, d):
    order, pairs, i = sorted(range(len(skills)), key=lambda x: skills[x]), [], 0
    while i + 1 < len(order):
        a, b = order[i], order[i + 1]
        if skills[b] - skills[a] <= d:
            pairs.append([a, b])
            i += 2
        else:
            i += 1
    return pairs
""", [[[1, 5, 2, 8], 1], [[], 3], [[4, 4, 4], 0], [[1, 10, 2, 11, 3], 1], [[7], 5], [[1, 2, 3, 4], 1]],
        [([[1, 5, 2, 8], 1], [[0, 2]]), ([[4, 4, 4], 0], [[0, 1]])],
        "O(n log n)", ("greedy", "sort", "two pointer", "adjacent"), checker="""
def check(args, got, expected):
    skills, d = args
    if not isinstance(got, list) or len(got) != len(expected):
        return False
    used = set()
    for pair in got:
        if not isinstance(pair, list) or len(pair) != 2:
            return False
        i, j = pair
        if not all(isinstance(x, int) and 0 <= x < len(skills) for x in pair) or i == j:
            return False
        if i in used or j in used or abs(skills[i] - skills[j]) > d:
            return False
        used |= {i, j}
    return True
""", statement="""
Implement `def max_fair_pairs(skills: List[int], d: int) -> List[List[int]]`.

skills[i] is player i's skill. Form as many pairs of players as possible so that no player is in
two pairs and the two skills in every pair differ by at most d. Return the pairs as index pairs
[i, j]. Any maximum set of pairs is accepted, in any order.

Example: skills = [1,5,2,8], d = 1 -> [[0,2]]
"""),
    Golden("novel-rate-limiter", "RateLimiter", [("operations", "List[str]"), ("arguments", "List[List]")], """
class RateLimiter:
    def __init__(self, limit, window):
        self.limit, self.window, self.calls = limit, window, collections.deque()

    def allow(self, t):
        while self.calls and self.calls[0] <= t - self.window:
            self.calls.popleft()
        if len(self.calls) < self.limit:
            self.calls.append(t)
            return True
        return False
""", [[["RateLimiter", "allow", "allow", "allow", "allow"], [[2, 10], [1], [2], [3], [11]]],
      [["RateLimiter", "allow", "allow", "allow"], [[1, 1], [5], [5], [6]]],
      [["RateLimiter", "allow", "allow", "allow", "allow"], [[3, 5], [0], [1], [4], [5]]]],
        [([["RateLimiter", "allow", "allow", "allow", "allow"], [[2, 10], [1], [2], [3], [11]]], [None, True, True, False, True])],
        "O(1)", ("queue", "deque", "window", "sliding"), kind="design", statement="""
Implement a class `RateLimiter`:
- `RateLimiter(limit: int, window: int)` creates the limiter.
- `allow(t: int) -> bool` is called with non-decreasing times. It returns True (and counts the
  call) if fewer than `limit` calls were allowed in the interval (t - window, t]; otherwise it
  returns False, and a rejected call is not counted.

Example: RateLimiter(2, 10), then allow(1) -> True, allow(2) -> True, allow(3) -> False, allow(11) -> True.
"""),
    Golden("novel-versioned-counter", "VersionedCounter", [("operations", "List[str]"), ("arguments", "List[List]")], """
class VersionedCounter:
    def __init__(self):
        self.version, self.history = 0, {}

    def inc(self, key):
        h = self.history.setdefault(key, [])
        count = h[-1][1] + 1 if h else 1
        if h and h[-1][0] == self.version:
            h[-1] = (self.version, count)
        else:
            h.append((self.version, count))

    def snapshot(self):
        self.version += 1
        return self.version - 1

    def get(self, key, version):
        h = self.history.get(key, [])
        i = bisect.bisect_right(h, (version, float("inf"))) - 1
        return h[i][1] if i >= 0 else 0
""", [[["VersionedCounter", "inc", "inc", "snapshot", "inc", "get", "get", "snapshot", "get"],
       [[], ["a"], ["a"], [], ["a"], ["a", 0], ["b", 0], [], ["a", 1]]],
      [["VersionedCounter", "snapshot", "snapshot", "inc", "get", "get"], [[], [], [], ["x"], ["x", 1], ["x", 0]]],
      [["VersionedCounter", "inc", "snapshot", "inc", "inc", "snapshot", "get", "get"], [[], ["k"], [], ["k"], ["k"], [], ["k", 0], ["k", 1]]]],
        [([["VersionedCounter", "inc", "inc", "snapshot", "inc", "get", "get", "snapshot", "get"],
           [[], ["a"], ["a"], [], ["a"], ["a", 0], ["b", 0], [], ["a", 1]]], [None, None, None, 0, None, 2, 0, 1, 3])],
        "O(log n)", ("binary search", "bisect", "history", "version", "snapshot"), kind="design", statement="""
Implement a class `VersionedCounter`:
- `VersionedCounter()` starts with every key at 0.
- `inc(key: str) -> None` adds 1 to key's count.
- `snapshot() -> int` returns a version id (0, 1, 2, ... in order) that captures every count at
  this moment.
- `get(key: str, version: int) -> int` returns key's count as it was in that snapshot.

Example: inc("a"), inc("a"), snapshot() -> 0, inc("a"), get("a", 0) -> 2, get("b", 0) -> 0.
"""),
    Golden("novel-count-no-adjacent-ones", "count_no_adjacent_ones", [("n", "int")], """
def count_no_adjacent_ones(n):
    fib = [1, 2]
    for _ in range(40):
        fib.append(fib[-1] + fib[-2])
    bits, total, prev = bin(n)[2:], 0, "0"
    for i, b in enumerate(bits):
        if b == "1":
            total += fib[len(bits) - i - 1]
            if prev == "1":
                return total
        prev = b
    return total + 1
""", [[0], [1], [3], [5], [10], [1000000]],
        [([5], 5), ([1], 2), ([0], 1), ([3], 3)],
        "O(log n)", ("dynamic", "dp", "digit", "fibonacci", "bit"), statement="""
Implement `def count_no_adjacent_ones(n: int) -> int`.

Return how many integers x with 0 <= x <= n have no two adjacent 1 bits in their binary form.
n can be as large as 10^9.
"""),
    Golden("novel-shortest-all-distinct", "shortest_all_distinct", [("s", "str")], """
def shortest_all_distinct(s):
    need, have, left, best, count = len(set(s)), 0, 0, len(s), {}
    for right, c in enumerate(s):
        count[c] = count.get(c, 0) + 1
        if count[c] == 1:
            have += 1
        while have == need and left <= right:
            best = min(best, right - left + 1)
            count[s[left]] -= 1
            if count[s[left]] == 0:
                have -= 1
            left += 1
    return best
""", [["aabcbcdbca"], ["aaaa"], [""], ["abc"], ["abacbca"], ["zzzyz"]],
        [(["aabcbcdbca"], 4), (["aaaa"], 1), ([""], 0), (["abc"], 3)],
        "O(n)", ("window", "sliding", "two pointer"), statement="""
Implement `def shortest_all_distinct(s: str) -> int`.

Return the length of the shortest contiguous piece of s that contains every distinct character of
s at least once. Return 0 for an empty string.
"""),
    Golden("novel-negatives-first", "negatives_first", [("head", "Optional[ListNode]")], """
def negatives_first(head):
    neg = neg_tail = ListNode()
    rest = rest_tail = ListNode()
    while head:
        if head.val < 0:
            neg_tail.next, neg_tail = head, head
        else:
            rest_tail.next, rest_tail = head, head
        head = head.next
    rest_tail.next = None
    neg_tail.next = rest.next
    return neg.next
""", [[[3, -1, 2, -5, 0]], [[]], [[-1, -2]], [[4, 5]], [[0, -3]], [[-7]]],
        [([[3, -1, 2, -5, 0]], [-1, -5, 3, 2, 0]), ([[]], []), ([[-1, -2]], [-1, -2])],
        "O(n)", ("pointer", "dummy", "partition", "linked list", "two list"), return_type="Optional[ListNode]", statement="""
Implement `def negatives_first(head: Optional[ListNode]) -> Optional[ListNode]`.

Rearrange a singly linked list so that every node with a negative value comes before every other
node. Keep the original relative order inside the negative group and inside the rest. Return the
new head.

Example: head = [3,-1,2,-5,0] -> [-1,-5,3,2,0]
"""),
    Golden("novel-depth-value-sum", "depth_value_sum", [("root", "Optional[TreeNode]")], """
def depth_value_sum(root):
    total, stack = 0, [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node:
            total += node.val if node.val == depth else 0
            stack += [(node.left, depth + 1), (node.right, depth + 1)]
    return total
""", [[[0, 1, 5, None, None, 2]], [[]], [[1]], [[0, 1, 1, 2, 2, 2, 2]], [[3, 1, None, 2, None, 3]]],
        [([[0, 1, 5, None, None, 2]], 3), ([[]], 0), ([[1]], 0), ([[0, 1, 1, 2, 2, 2, 2]], 10)],
        "O(n)", ("dfs", "bfs", "traversal", "recurs", "depth"), statement="""
Implement `def depth_value_sum(root: Optional[TreeNode]) -> int`.

The root of a binary tree has depth 0, its children depth 1, and so on. Return the sum of the
values of all nodes whose value equals their depth.

Example: root = [0,1,5,null,null,2] -> 3
"""),
]
