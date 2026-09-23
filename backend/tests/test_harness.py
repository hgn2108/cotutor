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
