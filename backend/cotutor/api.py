"""HTTP + WebSocket API.

A browser session opens ``/api/session`` and sends ``{"type": "solve", ...}``. The server
streams pipeline events back; whenever an agent needs code executed it sends an
``exec_request`` and the browser answers with ``exec_result`` from its Pyodide sandbox.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .cache import RunCache, replay
from .config import settings
from .executor import HARNESS_PATH, ClientExecutor
from .llm import GeminiClient, LLMClient
from .pipeline import Pipeline, PipelineConfig

PROBLEMS = json.loads((Path(__file__).parent / "data" / "problems.json").read_text())
MAX_PROBLEM_CHARS = 6000

app = FastAPI(title="Cotutor", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                   allow_methods=["GET"], allow_headers=["*"])
cache = RunCache(settings.cache_dir)


class RateLimiter:
    """Sliding-window limit on fresh (non-cached) runs per client, protecting the shared quota."""

    def __init__(self, limit: int, window_s: float = 3600):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client: str) -> bool:
        now, q = time.monotonic(), self.hits[client]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


limiter = RateLimiter(settings.runs_per_hour_per_ip)


def make_llm(user_key: str | None) -> LLMClient | None:
    key = user_key or settings.gemini_api_key
    if not key:
        return None
    return GeminiClient(key, settings.smart_models, settings.fast_models)


def make_solver(name: str):
    if name == "llama" and settings.llama_url:
        from .llama import LlamaSolver

        return LlamaSolver(settings.llama_url, settings.llama_token)
    return None


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "features": features()}


def features() -> dict[str, Any]:
    return {"server_key": bool(settings.gemini_api_key), "llama": bool(settings.llama_url),
            "models": {"smart": settings.smart_models[0], "fast": settings.fast_models[0]}}


@app.get("/api/problems")
def problems() -> list[dict[str, Any]]:
    return PROBLEMS


@app.get("/api/harness.py", response_class=PlainTextResponse)
def harness() -> str:
    return HARNESS_PATH.read_text()


@app.websocket("/api/session")
async def session(ws: WebSocket) -> None:
    await ws.accept()
    client = ws.headers.get("x-forwarded-for", ws.client.host if ws.client else "?").split(",")[0]
    send_lock = asyncio.Lock()

    async def send(msg: dict[str, Any]) -> None:
        async with send_lock:
            await ws.send_json(msg)

    executor = ClientExecutor(send)
    task: asyncio.Task | None = None
    await send({"type": "hello", "features": features()})
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "exec_result":
                executor.resolve(msg.get("id", ""), msg)
            elif msg.get("type") == "solve":
                if task and not task.done():
                    await send({"type": "error", "message": "A run is already in progress."})
                    continue
                task = asyncio.create_task(handle_solve(msg, send, executor, client))
            elif msg.get("type") == "cancel" and task:
                task.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        executor.cancel_all()
        if task:
            task.cancel()


async def handle_solve(msg: dict[str, Any], send, executor: ClientExecutor, client: str) -> None:
    problem = str(msg.get("problem", "")).strip()[:MAX_PROBLEM_CHARS]
    solver_name = msg.get("solver", "gemini")
    user_key = (msg.get("api_key") or "").strip() or None
    if len(problem) < 15:
        await send({"type": "error", "message": "Please paste a full problem statement."})
        return

    if not msg.get("fresh") and (record := cache.get(problem, solver_name)):
        await replay(record, send)
        return

    llm = make_llm(user_key)
    if llm is None:
        await send({"type": "error", "code": "no_key",
                    "message": "No Gemini API key is configured on this server. Add your own "
                               "free key in Settings, or try one of the recorded examples."})
        return
    if not user_key and not limiter.allow(client):
        await send({"type": "error", "code": "rate_limited",
                    "message": "Hourly limit for the shared key reached. Add your own free "
                               "Gemini key in Settings to keep going."})
        return

    events: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        events.append(ev)
        await send(ev)

    config = PipelineConfig(max_debug_attempts=settings.max_debug_attempts,
                            exec_timeout_s=settings.exec_timeout_s)
    await Pipeline(llm, executor, emit, config, solver=make_solver(solver_name)).run(problem)
    cache.put(problem, solver_name, events, {"recording": "live"})
