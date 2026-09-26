"""Execution harness shared by every sandbox.

This single stdlib-only file runs in two places:
  * in the browser, inside Pyodide in a Web Worker (the production sandbox), and
  * in a local subprocess (evals and tests: ``python harness.py < job.json``).

Entry point is ``run_job(job, emit)``. ``emit`` receives progress events (dicts) as work
happens, so if the host has to kill a runaway job it still knows which case hung and
which results were already finished.

Job kinds:
  tests         run the solution on test cases (expected values may come from a reference)
  differential  compare solution vs. a brute-force reference on randomly generated inputs
  complexity    time the solution on growing inputs and fit the log-log slope
  trace         record line-by-line execution state for the visualizer
"""

from __future__ import annotations

import collections
import copy
import io
import json
import math
import random
import sys
import time
import traceback
from contextlib import redirect_stdout

SOLUTION_FILE = "<solution>"
REFERENCE_FILE = "<reference>"
MAX_STDOUT = 2000
MAX_COLLECTION = 64


# --------------------------------------------------------------------------------------
# LeetCode-style data structures
# --------------------------------------------------------------------------------------
class ListNode:
    def __init__(self, val=0, next=None):  # noqa: A002 - LeetCode's signature
        self.val = val
        self.next = next

    def __repr__(self):
        return f"ListNode({self.val})"


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self):
        return f"TreeNode({self.val})"


def build_list(values):
    head = None
    for v in reversed(values or []):
        head = ListNode(v, head)
    return head


def list_to_values(node, limit=10_000):
    out, seen = [], 0
    while node is not None and seen < limit:
        out.append(node.val)
        node = node.next
        seen += 1
    return out


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue = collections.deque([root])
    i = 1
    while queue and i < len(values):
        node = queue.popleft()
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def tree_to_values(root):
    if root is None:
        return []
    out, queue = [], collections.deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


# --------------------------------------------------------------------------------------
# Loading code and converting arguments
# --------------------------------------------------------------------------------------
PRELUDE = (
    "from typing import *\n"
    "import collections, heapq, bisect, math, itertools, functools, string, re, operator\n"
    "from collections import defaultdict, deque, Counter, OrderedDict\n"
    "from heapq import heappush, heappop, heapify\n"
    "from functools import lru_cache, cache, reduce\n"
    "from itertools import accumulate, combinations, permutations, product\n"
    "from bisect import bisect_left, bisect_right, insort\n"
    "from math import inf, gcd, sqrt, ceil, floor\n"
)


def load_namespace(code, filename=SOLUTION_FILE):
    ns = {"__name__": "solution", "ListNode": ListNode, "TreeNode": TreeNode}
    exec(compile(PRELUDE, "<prelude>", "exec"), ns)
    exec(compile(code, filename, "exec"), ns)
    return ns


def resolve_callable(ns, entry):
    sol_cls = ns.get("Solution")
    if isinstance(sol_cls, type) and hasattr(sol_cls, entry):
        return getattr(sol_cls(), entry)
    fn = ns.get(entry)
    if callable(fn):
        return fn
    raise NameError(f"Could not find a function or Solution method named '{entry}'")


def _kind(type_str):
    t = (type_str or "").replace(" ", "")
    if "ListNode" in t:
        return "list_of_lists_nodes" if t.startswith(("List[", "list[")) else "listnode"
    if "TreeNode" in t:
        return "treenode"
    return "plain"


def convert_args(args, params):
    out = []
    for i, value in enumerate(args):
        kind = _kind(params[i].get("type") if i < len(params) else "")
        if isinstance(value, (ListNode, TreeNode)) or value is None:
            out.append(value)  # generators sometimes build nodes themselves
        elif kind == "listnode":
            out.append(build_list(value))
        elif kind == "list_of_lists_nodes":
            out.append([build_list(v) for v in value])
        elif kind == "treenode":
            out.append(build_tree(value))
        else:
            out.append(value)
    return out


def to_plain(value, depth=0):
    """Convert a return value to plain JSON-compatible data for comparison."""
    if depth > 50:
        return repr(value)
    if isinstance(value, ListNode):
        return list_to_values(value)
    if isinstance(value, TreeNode):
        return tree_to_values(value)
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value, (list, tuple, collections.deque)):
        return [to_plain(v, depth + 1) for v in value]
    if isinstance(value, (set, frozenset)):
        items = [to_plain(v, depth + 1) for v in value]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, dict):
        return {str(k): to_plain(v, depth + 1) for k, v in value.items()}
    return repr(value)


def _canon(x):
    return json.dumps(x, sort_keys=True)


def _floats_close(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return all(_floats_close(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def outputs_match(got, expected, comparison):
    if comparison == "float":
        return _floats_close(got, expected)
    if comparison in ("unordered", "unordered_nested") and isinstance(got, list) and isinstance(
        expected, list
    ):
        if comparison == "unordered_nested":
            def norm(v):
                return sorted(v, key=_canon) if isinstance(v, list) else v

            got = [norm(v) for v in got]
            expected = [norm(v) for v in expected]
        return sorted(map(_canon, got)) == sorted(map(_canon, expected))
    return got == expected


def load_checker(job):
    """Optional special judge: ``check(args, got, expected) -> bool`` for multi-answer problems."""
    if not job.get("checker_code"):
        return None
    return load_namespace(job["checker_code"], "<checker>")["check"]


def judge(checker, args, got, expected, comparison):
    if checker is not None:
        return bool(checker(copy.deepcopy(args), got, expected))
    return outputs_match(got, expected, comparison)


def run_design(cls, ops, op_args):
    """Replay LeetCode's design-problem format: construct, then call methods in order.

    ``[["LRUCache", "put", "get"], [[2], [1, 1], [1]]]`` -> ``[None, None, 1]``
    """
    if not ops:
        return []
    obj, out = cls(*op_args[0]), [None]
    for op, args in zip(ops[1:], op_args[1:], strict=True):
        out.append(to_plain(getattr(obj, op)(*args)))
    return out


class Runner:
    """How to call a solution, whatever its shape.

    A LeetCode function (or ``Solution`` method) is called with converted arguments; a design
    class is replayed through an operation sequence. Every job kind goes through this, so they
    all support both shapes.
    """

    def __init__(self, fn, spec):
        self.fn = fn
        self.params = spec.get("params", [])
        self.in_place = spec.get("in_place_arg")
        self.return_type = spec.get("return_type", "")
        self.design = spec.get("kind") == "design"

    def prepare(self, args):
        """Fresh, converted arguments (callers may mutate them)."""
        args = copy.deepcopy(args)
        return args if self.design else convert_args(args, self.params)

    def invoke(self, prepared):
        if self.design:
            return run_design(self.fn, *prepared)
        return self.fn(*prepared)

    def output(self, prepared, raw):
        """Plain JSON-able result, honouring in-place problems and empty lists/trees."""
        if not self.design and self.in_place is not None and self.in_place >= 0:
            raw = prepared[self.in_place]
        if raw is None and _kind(self.return_type) in ("listnode", "treenode"):
            raw = []  # an empty list/tree is None at runtime and [] in LeetCode's JSON
        return to_plain(raw)

    def __call__(self, args):
        """Run on a copy of ``args``; returns (plain_output, stdout)."""
        prepared = self.prepare(args)
        buf = io.StringIO()
        with redirect_stdout(buf):
            raw = self.invoke(prepared)
        return self.output(prepared, raw), buf.getvalue()[:MAX_STDOUT]


def bind(code, spec, filename=SOLUTION_FILE):
    return Runner(resolve_callable(load_namespace(code, filename), spec["entry"]), spec)


def format_error(exc):
    """Traceback restricted to frames from the user's own code."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == SOLUTION_FILE]
    lines = [f"line {f.lineno}, in {f.name}" for f in frames[-3:]]
    return {"type": type(exc).__name__, "message": str(exc)[:500], "where": lines}


# --------------------------------------------------------------------------------------
# Job kinds
# --------------------------------------------------------------------------------------
REFERENCE_STEP_CAP = 2_000_000  # ~1-2s of Python; brute force beyond this is "too slow to consult"


class _StepCap(Exception):
    pass


def with_step_cap(fn, *args, filename, cap):
    """Run ``fn(*args)``, raising _StepCap once code from ``filename`` executes ``cap`` lines.

    Used for the brute-force oracle: an exponential reference on a large input must not hang
    the whole job (and get blamed on the solution). Python can't be interrupted from outside
    inside Pyodide, but a trace function can stop it from the inside.
    """
    steps = 0

    def tracer(frame, event, arg):
        nonlocal steps
        if frame.f_code.co_filename != filename:
            return None
        if event == "line":
            steps += 1
            if steps >= cap:
                raise _StepCap()
        return tracer

    sys.settrace(tracer)
    try:
        return fn(*args)
    finally:
        sys.settrace(None)


def job_tests(job, emit):
    spec = job["spec"]
    comparison = spec["comparison"]
    run = bind(job["code"], spec)
    checker = load_checker(job)
    ref = None
    if job.get("reference_code"):
        try:
            ref = bind(job["reference_code"], spec, REFERENCE_FILE)
        except Exception as exc:  # a broken reference must not break the run
            emit({"ev": "reference_error", "error": format_error(exc)})

    ref_cap = job.get("reference_step_cap", REFERENCE_STEP_CAP)
    results = []
    for case in job["cases"]:
        emit({"ev": "case_start", "id": case["id"]})
        # A case "has" an expected value only if the key is present (None can be a real answer).
        expected, expected_source = case.get("expected"), "given"
        if "expected" not in case:
            expected_source = "none"
            if ref is not None:
                try:
                    expected, _ = with_step_cap(ref, case["args"], filename=REFERENCE_FILE, cap=ref_cap)
                    expected_source = "reference"
                except _StepCap:
                    # Too big for the brute force: still check the solution runs, and fast.
                    emit({"ev": "reference_too_slow", "id": case["id"]})
                except Exception as exc:
                    emit({"ev": "reference_error", "id": case["id"], "error": format_error(exc)})
        start = time.perf_counter()
        res = {"id": case["id"], "expected": expected, "expected_source": expected_source}
        try:
            got, out = run(case["args"])
            res.update(got=got, stdout=out)
            if expected_source != "none":
                ok = judge(checker, case["args"], got, expected, comparison)
                res["status"] = "pass" if ok else "fail"
            elif checker is not None:
                # No expected value, but a checker can still validate the answer directly.
                try:
                    res["status"] = "pass" if checker(copy.deepcopy(case["args"]), got, None) else "fail"
                except Exception:
                    res["status"] = "ran"
            else:
                res["status"] = "ran"  # nothing trustworthy to compare against
        except Exception as exc:
            res.update(status="error", error=format_error(exc))
        res["ms"] = round((time.perf_counter() - start) * 1000, 3)
        results.append(res)
        emit({"ev": "case_result", "result": res})
    return {"cases": results}


def job_differential(job, emit):
    spec = job["spec"]
    comparison = spec["comparison"]
    run = bind(job["code"], spec)
    ref = bind(job["reference_code"], spec, REFERENCE_FILE)
    checker = load_checker(job)
    generate = load_namespace(job["generator_code"], "<generator>")["generate"]
    rng = random.Random(job.get("seed", 0))
    sizes = job.get("sizes") or [1, 2, 3, 5, 8]
    budget = job.get("budget_s", 3.0)
    deadline = time.perf_counter() + budget
    ref_cap = job.get("reference_step_cap", REFERENCE_STEP_CAP)
    trials = ref_errors = 0
    for i in range(job.get("trials", 200)):
        if time.perf_counter() > deadline:
            break
        args = generate(rng, sizes[i % len(sizes)])
        try:
            expected, _ = with_step_cap(ref, args, filename=REFERENCE_FILE, cap=ref_cap)
        except Exception:  # includes _StepCap: skip inputs the brute force can't finish
            ref_errors += 1
            continue
        trials += 1
        emit({"ev": "trial", "n": trials})
        try:
            got, _ = run(args)
        except Exception as exc:
            return {"trials": trials, "reference_errors": ref_errors,
                    "counterexample": {"args": args, "expected": expected, "error": format_error(exc)}}
        if not judge(checker, args, got, expected, comparison):
            return {"trials": trials, "reference_errors": ref_errors,
                    "counterexample": {"args": args, "expected": expected, "got": got}}
    return {"trials": trials, "reference_errors": ref_errors, "counterexample": None}


def _pick_generator(gen_ns, job):
    """``which="random"`` forces generate(); otherwise prefer generate_worst when defined."""
    if job.get("which") == "random":
        return gen_ns["generate"]
    return gen_ns.get("generate_worst") or gen_ns["generate"]


def fit_slope(points):
    """Least-squares slope of log(ms) vs log(n)."""
    usable = [(math.log(n), math.log(ms)) for n, ms in points if ms > 0.2 and n > 0]
    if len(usable) < 3:
        return None
    mx = sum(x for x, _ in usable) / len(usable)
    my = sum(y for _, y in usable) / len(usable)
    num = sum((x - mx) * (y - my) for x, y in usable)
    den = sum((x - mx) ** 2 for x, _ in usable)
    return round(num / den, 3) if den else None


def job_complexity(job, emit):
    """Double n until one run is slow enough to time reliably, then fit the log-log slope.

    Uses ``generate_worst`` when the generator defines it, since random inputs often let a
    solution exit early and hide its true growth rate.
    """
    run = bind(job["code"], job["spec"])
    gen_ns = load_namespace(job["generator_code"], "<generator>")
    generate = _pick_generator(gen_ns, job)
    target_ms, max_n = job.get("target_ms", 60.0), job.get("max_n", 1 << 20)
    budget = job.get("budget_s", 6.0)
    seed = job.get("seed", 1)
    started, points, n = time.perf_counter(), [], job.get("start_n", 64)
    stopped, last_size = None, -1
    while n <= max_n:
        size = _input_size(generate(random.Random(seed + n), n))
        if size is not None and size <= last_size:
            # A generator that caps its output would make growth look flat; stop measuring.
            stopped = f"generator stopped growing at n={n // 2} (input size {last_size})"
            break
        last_size = size if size is not None else last_size
        best = None
        try:
            for _ in range(job.get("repeats", 3)):
                # Regenerate instead of deep-copying: copying a long ListNode chain recurses.
                a = run.prepare(generate(random.Random(seed + n), n))
                t0 = time.perf_counter()
                with redirect_stdout(io.StringIO()):
                    run.invoke(a)
                elapsed = (time.perf_counter() - t0) * 1000
                best = elapsed if best is None else min(best, elapsed)
                if best > target_ms:
                    break
        except (RecursionError, MemoryError) as exc:
            stopped = f"stopped at n={n}: {type(exc).__name__}"  # keep the points we have
            break
        points.append([n, round(best, 4)])
        emit({"ev": "point", "n": n, "ms": best})
        if best >= target_ms or time.perf_counter() - started > budget:
            break
        n *= 2
    return {"points": points, "slope": fit_slope(points), "stopped": stopped,
            "used_worst_case": generate is gen_ns.get("generate_worst")}


def _input_size(args):
    """Total length of the list/str/node-chain arguments, or None if there are none."""
    total, found = 0, False
    for a in args:
        if isinstance(a, (list, str, tuple)):
            total, found = total + len(a), True
        elif isinstance(a, ListNode):
            total, found = total + len(list_to_values(a)), True
    return total if found else None


def snapshot(value, depth=0):
    """Typed, size-limited JSON snapshot of a runtime value for the visualizer."""
    if depth > 4:
        return {"t": "more"}
    if value is None or isinstance(value, (bool, int, str)):
        return value if not isinstance(value, str) or len(value) < 200 else value[:200] + "…"
    if isinstance(value, float):
        return value if math.isfinite(value) else {"t": "num", "repr": repr(value)}
    if isinstance(value, ListNode):
        return {"t": "linked", "values": [snapshot(v, depth + 1) for v in list_to_values(value, 40)],
                "id": id(value)}
    if isinstance(value, TreeNode):
        return {"t": "tree", "values": tree_to_values(value)[:127], "id": id(value)}
    if isinstance(value, (list, tuple, collections.deque)):
        kind = {list: "list", tuple: "tuple"}.get(type(value), "deque")
        items = list(value)
        return {"t": kind, "values": [snapshot(v, depth + 1) for v in items[:MAX_COLLECTION]],
                "len": len(items)}
    if isinstance(value, (set, frozenset)):
        items = sorted(value, key=repr)[:MAX_COLLECTION]
        return {"t": "set", "values": [snapshot(v, depth + 1) for v in items], "len": len(value)}
    if isinstance(value, dict):
        items = list(value.items())[:MAX_COLLECTION]
        return {"t": "dict", "entries": [[snapshot(k, depth + 1), snapshot(v, depth + 1)]
                                         for k, v in items], "len": len(value)}
    if callable(value) or isinstance(value, type):
        return None
    return {"t": "obj", "repr": repr(value)[:120]}


def job_trace(job, emit):
    run = bind(job["code"], job["spec"])
    max_steps = job.get("max_steps", 600)
    max_bytes = job.get("max_bytes", 1_500_000)
    steps, truncated, size = [], False, [0]

    def tracer(frame, event, arg):
        nonlocal truncated
        if frame.f_code.co_filename != SOLUTION_FILE:
            return None
        if len(steps) >= max_steps:
            truncated = True
            sys.settrace(None)
            return None
        if event in ("line", "call", "return"):
            depth, f = 0, frame
            while f is not None:
                depth += f.f_code.co_filename == SOLUTION_FILE
                f = f.f_back
            local_vars = {}
            for name, v in frame.f_locals.items():
                if name.startswith("__"):
                    continue
                if name == "self":
                    # Design problems keep their state on the object: show its fields.
                    for attr, av in getattr(v, "__dict__", {}).items():
                        snap = snapshot(av)
                        if snap is not None or av is None:
                            local_vars[f"self.{attr}"] = snap
                    continue
                snap = snapshot(v)
                if snap is not None or v is None:
                    local_vars[name] = snap
            step = {"event": event, "line": frame.f_lineno, "func": frame.f_code.co_name,
                    "depth": depth, "locals": local_vars}
            if event == "return":
                step["ret"] = snapshot(arg)
            # Grids snapshotted at every step add up fast; keep the payload browser-sized.
            size[0] += len(json.dumps(step, default=str))
            if size[0] > max_bytes:
                truncated = True
                sys.settrace(None)
                return None
            steps.append(step)
        return tracer

    prepared = run.prepare(job["args"])
    buf, error, result = io.StringIO(), None, None
    sys.settrace(tracer)
    try:
        with redirect_stdout(buf):
            result = run.output(prepared, run.invoke(prepared))
    except Exception as exc:
        error = format_error(exc)
    finally:
        sys.settrace(None)
    return {"steps": steps, "truncated": truncated, "result": result,
            "error": error, "stdout": buf.getvalue()[:MAX_STDOUT]}


def job_line_counts(job, emit):
    """Count how many times each line runs on small inputs of growing size.

    Exact, discrete step counts make growth visible to a learner ("this line ran 16, 64, 256
    times") in a way wall-clock timings can't. Sizes stop early once a run gets too big.
    """
    run = bind(job["code"], job["spec"])
    gen_ns = load_namespace(job["generator_code"], "<generator>")
    generate = _pick_generator(gen_ns, job)
    cap = job.get("max_events", 200_000)
    deadline = time.perf_counter() + job.get("budget_s", 4.0)
    runs = []
    for n in job.get("sizes") or [4, 8, 16, 32]:
        if time.perf_counter() > deadline:
            break
        # Random inputs are averaged over several seeds; one sample is too noisy at small n.
        trials = max(1, job.get("trials", 1))
        counts, total, capped = {}, 0, False
        for t in range(trials):
            prepared = run.prepare(generate(random.Random(job.get("seed", 7) + t), n))
            c, tot, cap_hit = _count_lines(run, prepared, cap)
            for line, v in c.items():
                counts[line] = counts.get(line, 0) + v
            total, capped = total + tot, capped or cap_hit
        counts = {k: round(v / trials) for k, v in counts.items()}
        total = round(total / trials)
        runs.append({"n": n, "total": total, "capped": capped,
                     "counts": {str(k): v for k, v in sorted(counts.items())}})
        emit({"ev": "point", "n": n, "total": total})
        if capped:
            break
    return {"runs": runs, "used_worst_case": generate is gen_ns.get("generate_worst")}


def _count_lines(run, prepared, cap):
    counts, total = {}, 0

    def tracer(frame, event, arg):
        nonlocal total
        if frame.f_code.co_filename != SOLUTION_FILE:
            return None
        if event == "line":
            counts[frame.f_lineno] = counts.get(frame.f_lineno, 0) + 1
            total += 1
            if total >= cap:
                raise _StepCap()
        return tracer

    capped = False
    sys.settrace(tracer)
    try:
        with redirect_stdout(io.StringIO()):
            run.invoke(prepared)
    except _StepCap:
        capped = True
    finally:
        sys.settrace(None)
    return counts, total, capped


JOBS = {"tests": job_tests, "differential": job_differential,
        "complexity": job_complexity, "trace": job_trace, "line_counts": job_line_counts}


def run_job(job, emit=None):
    emit = emit or (lambda _ev: None)
    try:
        return {"ok": True, **JOBS[job["kind"]](job, emit)}
    except SyntaxError as exc:
        return {"ok": False, "error": {"type": "SyntaxError", "message": exc.msg,
                                       "where": [f"line {exc.lineno}"]}}
    except Exception as exc:
        return {"ok": False, "error": format_error(exc) | {"type": type(exc).__name__}}


def run_job_json(job_json, emit_json=None):
    """Pyodide entry point: JSON string in, JSON string out; events forwarded as JSON."""
    emit = (lambda ev: emit_json(json.dumps(ev))) if emit_json else None
    return json.dumps(run_job(json.loads(job_json), emit))


if __name__ == "__main__":
    out = sys.stdout
    sys.setrecursionlimit(10_000)

    def _emit(ev):
        out.write("@@EV " + json.dumps(ev) + "\n")
        out.flush()

    result = run_job(json.loads(sys.stdin.read()), _emit)
    out.write("@@RESULT " + json.dumps(result) + "\n")
    out.flush()
