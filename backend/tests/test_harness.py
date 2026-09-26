"""Harness behaviour on LeetCode's node-based problems."""

import json
import subprocess
import sys

from cotutor.executor import HARNESS_PATH


def run(job):
    out = subprocess.run([sys.executable, str(HARNESS_PATH)], input=json.dumps(job),
                         capture_output=True, text=True, timeout=30).stdout
    return json.loads(next(line for line in out.splitlines() if line.startswith("@@RESULT "))[9:])


REVERSE = {"entry": "reverseList", "params": [{"name": "head", "type": "Optional[ListNode]"}],
           "return_type": "Optional[ListNode]", "comparison": "exact"}
CODE = """
class Solution:
    def reverseList(self, head):
        prev = None
        while head:
            head.next, prev, head = prev, head, head.next
        return prev
"""


def test_none_for_empty_linked_list_equals_empty_json_list():
    res = run({"kind": "tests", "spec": REVERSE, "code": CODE,
               "cases": [{"id": "empty", "args": [[]], "expected": []},
                         {"id": "three", "args": [[1, 2, 3]], "expected": [3, 2, 1]}]})
    assert [c["status"] for c in res["cases"]] == ["pass", "pass"]


def test_generators_may_build_nodes_themselves():
    gen = """
def generate(rng, n):
    head = None
    for v in range(n):
        head = ListNode(v, head)
    return [head]
"""
    res = run({"kind": "line_counts", "spec": REVERSE, "code": CODE, "generator_code": gen,
               "sizes": [4, 8]})
    assert res["ok"] and [r["n"] for r in res["runs"]] == [4, 8]


def test_tree_input_and_depth():
    spec = {"entry": "maxDepth", "params": [{"name": "root", "type": "Optional[TreeNode]"}],
            "return_type": "int", "comparison": "exact"}
    code = ("def maxDepth(root):\n"
            "    return 0 if not root else 1 + max(maxDepth(root.left), maxDepth(root.right))\n")
    res = run({"kind": "tests", "spec": spec, "code": code,
               "cases": [{"id": "a", "args": [[3, 9, 20, None, None, 15, 7]], "expected": 3},
                         {"id": "b", "args": [[]], "expected": 0}]})
    assert [c["status"] for c in res["cases"]] == ["pass", "pass"]


def test_complexity_on_long_linked_lists_and_deep_recursion():
    gen = "def generate(rng, n):\n    return [list(range(n))]\n"
    res = run({"kind": "complexity", "spec": REVERSE, "code": CODE, "generator_code": gen, "budget_s": 4})
    assert res["ok"] and res["slope"] is not None and 0.6 < res["slope"] < 1.5

    recursive = ("def reverseList(head):\n"
                 "    if not head or not head.next:\n        return head\n"
                 "    new = reverseList(head.next)\n"
                 "    head.next.next = head\n    head.next = None\n    return new\n")
    res = run({"kind": "complexity", "spec": REVERSE, "code": recursive, "generator_code": gen,
               "budget_s": 4})
    assert res["ok"] and res["points"]  # deep recursion ends the sweep but keeps the points


def test_capped_generator_does_not_fake_a_flat_growth_rate():
    spec = {"entry": "f", "params": [{"name": "nums", "type": "List[int]"}], "comparison": "exact"}
    quadratic = "def f(nums):\n    return sum(1 for a in nums for b in nums if a < b)\n"
    capped = "def generate(rng, n):\n    return [list(range(min(n, 300)))]\n"
    res = run({"kind": "complexity", "spec": spec, "code": quadratic, "generator_code": capped})
    assert "stopped growing" in res["stopped"]
    assert all(n <= 512 for n, _ in res["points"])


def test_slow_brute_force_does_not_hang_or_blame_the_solution():
    spec = {"entry": "coinChange", "params": [{"name": "coins", "type": "List[int]"},
                                              {"name": "amount", "type": "int"}],
            "return_type": "int", "comparison": "exact"}
    exponential_ref = (
        "def coinChange(coins, amount):\n"
        "    def go(rem):\n"
        "        if rem == 0: return 0\n"
        "        if rem < 0: return -1\n"
        "        best = -1\n"
        "        for c in coins:\n"
        "            r = go(rem - c)\n"
        "            if r >= 0 and (best < 0 or r + 1 < best): best = r + 1\n"
        "        return best\n"
        "    return go(amount)\n")
    dp = ("def coinChange(coins, amount):\n"
          "    INF = amount + 1\n    best = [0] + [INF] * amount\n"
          "    for a in range(1, amount + 1):\n"
          "        for c in coins:\n"
          "            if c <= a: best[a] = min(best[a], best[a - c] + 1)\n"
          "    return -1 if best[amount] == INF else best[amount]\n")
    res = run({"kind": "tests", "spec": spec, "code": dp, "reference_code": exponential_ref,
               "reference_step_cap": 200_000,
               "cases": [{"id": "small", "args": [[1, 2, 5], 11]},
                         {"id": "huge", "args": [[1, 2, 5], 300]}]})
    by_id = {c["id"]: c for c in res["cases"]}
    assert by_id["small"]["status"] == "pass" and by_id["small"]["expected"] == 3
    assert by_id["huge"]["status"] == "ran" and by_id["huge"]["expected_source"] == "none"


def test_trace_of_a_big_grid_stays_browser_sized():
    spec = {"entry": "count", "params": [{"name": "grid", "type": "List[List[str]]"}],
            "return_type": "int", "comparison": "exact"}
    code = ("def count(grid):\n    total = 0\n"
            "    for r in range(len(grid)):\n        for c in range(len(grid[0])):\n"
            "            total += grid[r][c] == '1'\n    return total\n")
    grid = [["1" if (r + c) % 2 else "0" for c in range(60)] for r in range(60)]
    res = run({"kind": "trace", "spec": spec, "code": code, "args": [grid], "max_bytes": 200_000})
    assert res["ok"] and res["truncated"]
    assert len(json.dumps(res)) < 400_000


LRU_SPEC = {"entry": "LRUCache", "kind": "design", "comparison": "exact", "return_type": "",
            "params": [{"name": "operations", "type": "List[str]"},
                       {"name": "arguments", "type": "List[List]"}]}
LRU = """
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
"""
LRU_NAIVE = """
class LRUCache:
    def __init__(self, capacity):
        self.capacity, self.items = capacity, []   # [key, value], least recent first

    def get(self, key):
        for i, (k, v) in enumerate(self.items):
            if k == key:
                self.items.append(self.items.pop(i))
                return v
        return -1

    def put(self, key, value):
        self.items = [kv for kv in self.items if kv[0] != key] + [[key, value]]
        if len(self.items) > self.capacity:
            self.items.pop(0)
"""
LRU_GEN = """
def generate(rng, n):
    ops, args = ["LRUCache"], [[rng.randint(1, 4)]]
    for _ in range(n):
        if rng.random() < 0.5:
            ops.append("put"); args.append([rng.randint(1, 6), rng.randint(0, 99)])
        else:
            ops.append("get"); args.append([rng.randint(1, 6)])
    return [ops, args]
"""
LEETCODE_EXAMPLE = [["LRUCache", "put", "put", "get", "put", "get", "put", "get", "get", "get"],
                    [[2], [1, 1], [2, 2], [1], [3, 3], [2], [4, 4], [1], [3], [4]]]


def test_design_problem_replays_operation_sequences():
    res = run({"kind": "tests", "spec": LRU_SPEC, "code": LRU, "reference_code": LRU_NAIVE,
               "cases": [{"id": "ex", "args": LEETCODE_EXAMPLE,
                          "expected": [None, None, None, 1, None, -1, None, -1, 3, 4]},
                         {"id": "gen", "args": [["LRUCache", "put", "get"], [[1], [5, 5], [5]]]}]})
    assert [c["status"] for c in res["cases"]] == ["pass", "pass"]
    assert res["cases"][1]["expected"] == [None, None, 5]


def test_design_differential_catches_a_broken_eviction():
    broken = LRU.replace("self.cache.move_to_end(key)\n        return", "return")  # get() forgets recency
    res = run({"kind": "differential", "spec": LRU_SPEC, "code": broken, "reference_code": LRU_NAIVE,
               "generator_code": LRU_GEN, "sizes": [6, 10, 16], "trials": 300})
    assert res["counterexample"] is not None


def test_design_trace_shows_object_fields_and_counts_work():
    res = run({"kind": "trace", "spec": LRU_SPEC, "code": LRU, "args": LEETCODE_EXAMPLE})
    assert res["result"] == [None, None, None, 1, None, -1, None, -1, 3, 4]
    assert any("self.cache" in s["locals"] for s in res["steps"])
    counts = run({"kind": "line_counts", "spec": LRU_SPEC, "code": LRU, "generator_code": LRU_GEN,
                  "sizes": [8, 16, 32]})
    assert counts["ok"] and len(counts["runs"]) == 3


def spec_of(entry, params, ret="", kind="function"):
    return {"entry": entry, "kind": kind, "comparison": "exact", "return_type": ret,
            "params": [{"name": n, "type": t} for n, t in params]}


CLONE = """
def cloneGraph(node):
    if not node:
        return None
    copies = {}
    def copy(n):
        if n not in copies:
            copies[n] = Node(n.val)
            copies[n].neighbors = [copy(m) for m in n.neighbors]
        return copies[n]
    return copy(node)
"""


def test_clone_graph_requires_a_real_deep_copy():
    spec = spec_of("cloneGraph", [("node", "Optional[GraphNode]")], "Optional[GraphNode]")
    cases = [{"id": "a", "args": [[[2, 4], [1, 3], [2, 4], [1, 3]]], "expected": [[2, 4], [1, 3], [2, 4], [1, 3]]},
             {"id": "empty", "args": [[]], "expected": []}]
    ok = run({"kind": "tests", "spec": spec, "code": CLONE, "cases": cases})
    assert [c["status"] for c in ok["cases"]] == ["pass", "pass"]
    cheat = run({"kind": "tests", "spec": spec, "code": "def cloneGraph(node):\n    return node\n", "cases": cases[:1]})
    assert cheat["cases"][0]["status"] == "fail"
    assert "deep copy" in str(cheat["cases"][0]["got"])


def test_copy_random_list_round_trips_pointers():
    spec = spec_of("copyRandomList", [("head", "Optional[RandomNode]")], "Optional[RandomNode]")
    code = """
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
"""
    pairs = [[7, None], [13, 0], [11, 4], [10, 2], [1, 0]]
    res = run({"kind": "tests", "spec": spec, "code": code, "cases": [{"id": "a", "args": [pairs], "expected": pairs}]})
    assert res["cases"][0]["status"] == "pass"


def test_cyclic_lists_and_node_references():
    cyc = spec_of("hasCycle", [("head", "Optional[ListNode]")], "bool")
    code = ("def hasCycle(head):\n    slow = fast = head\n    while fast and fast.next:\n"
            "        slow, fast = slow.next, fast.next.next\n        if slow is fast:\n"
            "            return True\n    return False\n")
    res = run({"kind": "tests", "spec": cyc, "code": code, "cases": [
        {"id": "loop", "args": [{"values": [3, 2, 0, -4], "pos": 1}], "expected": True},
        {"id": "none", "args": [{"values": [1, 2], "pos": -1}], "expected": False}]})
    assert [c["status"] for c in res["cases"]] == ["pass", "pass"]

    lca = spec_of("lowestCommonAncestor", [("root", "TreeNode"), ("p", "TreeNode"), ("q", "TreeNode")], "TreeNode")
    code = ("def lowestCommonAncestor(root, p, q):\n    while root:\n"
            "        if p.val < root.val and q.val < root.val: root = root.left\n"
            "        elif p.val > root.val and q.val > root.val: root = root.right\n"
            "        else: return root\n")
    tree = [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5]
    res = run({"kind": "tests", "spec": lca, "code": code, "cases": [
        {"id": "a", "args": [tree, 2, 8], "expected": tree},
        {"id": "b", "args": [tree, 2, 4], "expected": [2, 0, 4, None, None, 3, 5]}]})
    assert [c["status"] for c in res["cases"]] == ["pass", "pass"]


def test_codecs_round_trip_and_must_produce_strings():
    spec = spec_of("Codec", [("root", "Optional[TreeNode]")], "Optional[TreeNode]", kind="codec")
    good = """
class Codec:
    def serialize(self, root):
        out = []
        def go(n):
            if not n:
                out.append("#"); return
            out.append(str(n.val)); go(n.left); go(n.right)
        go(root)
        return ",".join(out)

    def deserialize(self, data):
        vals = iter(data.split(","))
        def go():
            v = next(vals)
            if v == "#":
                return None
            n = TreeNode(int(v)); n.left = go(); n.right = go()
            return n
        return go()
"""
    tree = [1, 2, 3, None, None, 4, 5]
    res = run({"kind": "tests", "spec": spec, "code": good, "cases": [
        {"id": "a", "args": [tree], "expected": tree}, {"id": "empty", "args": [[]], "expected": []}]})
    assert [c["status"] for c in res["cases"]] == ["pass", "pass"]
    lazy = "class Codec:\n    def serialize(self, root):\n        return root\n    def deserialize(self, data):\n        return data\n"
    res = run({"kind": "tests", "spec": spec, "code": lazy, "cases": [{"id": "a", "args": [tree], "expected": tree}]})
    assert res["cases"][0]["status"] == "error" and "must return a string" in res["cases"][0]["error"]["message"]
