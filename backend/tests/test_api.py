"""End-to-end over the real WebSocket protocol: the test plays the browser, fulfilling
exec_requests with the local harness exactly as the Pyodide worker would."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from cotutor.cache import RunCache
from cotutor.executor import LocalExecutor
from cotutor.llm import ScriptedLLM
from cotutor.server import app as server_app
from cotutor.server import deps

from .fixtures import two_sum_script

PROBLEM = "Given nums and target, return indices of two numbers adding up to target."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "cache", RunCache(tmp_path))
    monkeypatch.setattr(deps, "make_llm", lambda key: ScriptedLLM(two_sum_script()))
    return TestClient(server_app.app)


def drive_session(ws, message):
    """Send a solve request and act as the browser sandbox until the run is done."""
    ws.send_json(message)
    local, events = LocalExecutor(), []
    while True:
        msg = ws.receive_json()
        if msg["type"] == "exec_request":
            result = asyncio.run(local.run(msg["job"], msg["timeout_s"]))
            ws.send_json({"type": "exec_result", "id": msg["id"], "result": result})
            continue
        if msg["type"] == "problem":
            continue
        events.append(msg)
        if msg["type"] in ("done", "error"):
            return events


def test_http_endpoints(client):
    assert client.get("/api/health").json()["ok"] is True
    assert len(client.get("/api/problems").json()) >= 10
    assert "def run_job" in client.get("/api/harness.py").text


def test_full_session_then_cached_replay(client):
    with client.websocket_connect("/api/session") as ws:
        assert ws.receive_json()["type"] == "hello"
        events = drive_session(ws, {"type": "solve", "problem": PROBLEM})
        assert events[-1]["summary"]["verified"] is True

        replayed = drive_session(ws, {"type": "solve", "problem": PROBLEM})
        assert replayed[-1]["summary"]["replayed"] is True
        assert [e["type"] for e in replayed] == [e["type"] for e in events]


def test_rejects_too_short(client):
    with client.websocket_connect("/api/session") as ws:
        ws.receive_json()
        events = drive_session(ws, {"type": "solve", "problem": "hi"})
        assert events[-1]["type"] == "error"


def test_websocket_rejects_foreign_origins(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/session", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_origin_rules():
    from cotutor.config import Settings

    s = Settings(allowed_origins=["https://cotutor.vercel.app"],
                 allowed_origin_regex=r"^https://cotutor(-[a-z0-9-]+)?\.vercel\.app$")
    assert s.origin_allowed("https://cotutor.vercel.app")
    assert s.origin_allowed("https://cotutor-git-main-hgn2108.vercel.app")
    assert not s.origin_allowed("https://cotutor.vercel.app.evil.com")
    assert not s.origin_allowed("http://localhost:3000")
    assert s.origin_allowed(None)
