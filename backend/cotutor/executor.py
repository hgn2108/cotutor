"""Code execution is a tool the agents call; *where* it runs is pluggable.

* ``ClientExecutor``  forwards jobs over the WebSocket to the user's browser, which runs them
                      in Pyodide. The server never executes untrusted code, which is what makes
                      free shared hosting safe.
* ``LocalExecutor``   runs the same harness in a local subprocess (evals, tests, CLI).

Both return the harness result dict. On timeout they rebuild a partial result from the
progress events the harness streamed before it was killed (see ``finalize_timeout``).
"""

from __future__ import annotations

import asyncio
import itertools
import json
import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol

HARNESS_PATH = Path(__file__).parent / "runtime" / "harness.py"


class Executor(Protocol):
    async def run(self, job: dict[str, Any], timeout_s: float) -> dict[str, Any]: ...


def finalize_timeout(job: dict[str, Any], events: list[dict[str, Any]], timeout_s: float) -> dict:
    """Build a best-effort result for a job that was killed after ``timeout_s``."""
    base = {"ok": True, "timed_out": True}
    kind = job["kind"]
    if kind == "tests":
        done = {e["result"]["id"]: e["result"] for e in events if e.get("ev") == "case_result"}
        started = [e["id"] for e in events if e.get("ev") == "case_start"]
        hung = next((cid for cid in reversed(started) if cid not in done), None)
        cases = []
        for case in job["cases"]:
            if case["id"] in done:
                cases.append(done[case["id"]])
            elif case["id"] == hung:
                cases.append({"id": hung, "status": "timeout",
                              "error": {"type": "Timeout", "where": [],
                                        "message": f"No result after {timeout_s:.0f}s "
                                                   "(infinite loop or far too slow?)"}})
            else:
                cases.append({"id": case["id"], "status": "skipped"})
        return base | {"cases": cases}
    if kind == "differential":
        trials = max((e["n"] for e in events if e.get("ev") == "trial"), default=0)
        return base | {"trials": trials, "reference_errors": 0, "counterexample": None}
    if kind == "complexity":
        from .runtime.harness import fit_slope

        points = [[e["n"], e["ms"]] for e in events if e.get("ev") == "point"]
        return base | {"points": points, "slope": fit_slope(points)}
    return {"ok": False, "timed_out": True,
            "error": {"type": "Timeout", "message": f"Timed out after {timeout_s:.0f}s", "where": []}}


class LocalExecutor:
    """Runs the harness in a subprocess with a minimal environment (no API keys)."""

    async def run(self, job, timeout_s):
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-I", str(HARNESS_PATH),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"},
        )
        events: list[dict] = []
        result: dict | None = None

        async def pump() -> None:
            nonlocal result
            assert proc.stdin and proc.stdout
            proc.stdin.write(json.dumps(job).encode())
            await proc.stdin.drain()
            proc.stdin.close()
            async for raw in proc.stdout:
                line = raw.decode(errors="replace")
                if line.startswith("@@EV "):
                    events.append(json.loads(line[5:]))
                elif line.startswith("@@RESULT "):
                    result = json.loads(line[9:])

        try:
            await asyncio.wait_for(pump(), timeout_s)
            await proc.wait()
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return finalize_timeout(job, events, timeout_s)
        if result is None:
            return {"ok": False, "error": {"type": "Crash", "where": [],
                                           "message": "Process exited without a result "
                                                      "(recursion or memory limit?)"}}
        return result


Send = Callable[[dict[str, Any]], Awaitable[None]]


class ClientExecutor:
    """Bridges execution jobs to the browser over an existing WebSocket session."""

    def __init__(self, send: Send, grace_s: float = 20.0):
        self._send = send
        self._pending: dict[str, asyncio.Future] = {}
        self._ids = itertools.count(1)
        # Allowance for Pyodide cold start and network latency on top of the job timeout.
        self._grace_s = grace_s

    async def run(self, job, timeout_s):
        job_id = f"job-{next(self._ids)}"
        fut = asyncio.get_running_loop().create_future()
        self._pending[job_id] = fut
        await self._send({"type": "exec_request", "id": job_id, "job": job, "timeout_s": timeout_s})
        try:
            reply = await asyncio.wait_for(fut, timeout_s + self._grace_s)
        except TimeoutError:
            return finalize_timeout(job, [], timeout_s)
        finally:
            self._pending.pop(job_id, None)
        if reply.get("timed_out"):
            return finalize_timeout(job, reply.get("events", []), timeout_s)
        return reply.get("result") or {"ok": False, "error": {"type": "ClientError", "where": [],
                                                              "message": "Empty result"}}

    def resolve(self, job_id: str, reply: dict[str, Any]) -> None:
        fut = self._pending.get(job_id)
        if fut and not fut.done():
            fut.set_result(reply)

    def cancel_all(self) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
