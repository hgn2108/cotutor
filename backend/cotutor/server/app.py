"""HTTP routes and the WebSocket endpoint. Run with ``uvicorn cotutor.server.app:app``."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .. import library
from ..config import settings
from ..executor import HARNESS_PATH
from . import deps
from .session import Session

app = FastAPI(title="Cotutor", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                   allow_methods=["GET"], allow_headers=["*"])


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "features": deps.features()}


@app.get("/api/problems")
def problems() -> list[dict[str, Any]]:
    return library.problems()


@app.get("/api/harness.py", response_class=PlainTextResponse)
def harness() -> str:
    """The execution harness, loaded into the browser's Pyodide sandbox."""
    return HARNESS_PATH.read_text()


@app.websocket("/api/session")
async def session(ws: WebSocket) -> None:
    await Session(ws).serve()
