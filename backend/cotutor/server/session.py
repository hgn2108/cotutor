"""One browser session over a WebSocket.

The browser sends ``{"type": "solve", ...}``; the server streams pipeline events back. When an
agent needs code executed, the server sends an ``exec_request`` and the browser answers with
``exec_result`` from its Pyodide sandbox, so untrusted code never runs on the server.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..cache import replay
from ..config import settings
from ..executor import ClientExecutor
from ..pipeline import Pipeline, PipelineConfig
from . import deps

MAX_PROBLEM_CHARS = 6000
MIN_PROBLEM_CHARS = 15


class Session:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        forwarded = ws.headers.get("x-forwarded-for")
        self.client = (forwarded or (ws.client.host if ws.client else "?")).split(",")[0].strip()
        self._send_lock = asyncio.Lock()
        self.executor = ClientExecutor(self.send)
        self.task: asyncio.Task | None = None

    async def send(self, msg: dict[str, Any]) -> None:
        async with self._send_lock:
            await self.ws.send_json(msg)

    async def serve(self) -> None:
        if not settings.origin_allowed(self.ws.headers.get("origin")):
            await self.ws.close(code=1008)  # policy violation: not one of our frontends
            return
        await self.ws.accept()
        await self.send({"type": "hello", "features": deps.features()})
        try:
            while True:
                await self._dispatch(await self.ws.receive_json())
        except WebSocketDisconnect:
            pass
        finally:
            self.executor.cancel_all()
            if self.task:
                self.task.cancel()

    async def _dispatch(self, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind == "exec_result":
            self.executor.resolve(msg.get("id", ""), msg)
        elif kind == "solve":
            if self.task and not self.task.done():
                await self.send({"type": "error", "message": "A run is already in progress."})
            else:
                self.task = asyncio.create_task(self._solve(msg))
        elif kind == "cancel" and self.task:
            self.task.cancel()

    async def _solve(self, msg: dict[str, Any]) -> None:
        problem = str(msg.get("problem", "")).strip()[:MAX_PROBLEM_CHARS]
        user_key = (msg.get("api_key") or "").strip() or None
        if len(problem) < MIN_PROBLEM_CHARS:
            await self.send({"type": "error", "message": "Please paste a full problem statement."})
            return

        if not msg.get("fresh") and (record := deps.cache.get(problem)):
            await replay(record, self.send)
            return

        llm = deps.make_llm(user_key)
        if llm is None:
            await self.send({"type": "error", "code": "no_key",
                             "message": "No Gemini API key is configured on this server. Add your "
                                        "own free key in Settings, or try one of the examples."})
            return
        if not user_key and not deps.limiter.allow(self.client):
            await self.send({"type": "error", "code": "rate_limited",
                             "message": "Hourly limit for the shared key reached. Add your own "
                                        "free Gemini key in Settings to keep going."})
            return

        events: list[dict[str, Any]] = []

        async def emit(ev: dict[str, Any]) -> None:
            events.append(ev)
            await self.send(ev)

        config = PipelineConfig(max_debug_attempts=settings.max_debug_attempts,
                                exec_timeout_s=settings.exec_timeout_s)
        await Pipeline(llm, self.executor, emit, config).run(problem)
        deps.cache.put(problem, events, {"recording": "live"})
