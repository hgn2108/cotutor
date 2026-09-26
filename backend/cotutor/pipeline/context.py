"""Shared plumbing for one pipeline run: config, stats, stage reporting and the execution tool."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ..executor import Executor
from ..llm import LLMClient, Usage
from ..schemas import ProblemSpec

Emit = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class PipelineConfig:
    max_debug_attempts: int = 3
    exec_timeout_s: float = 8.0
    differential_trials: int = 300


@dataclass
class RunStats:
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    started: float = field(default_factory=time.perf_counter)

    def elapsed_ms(self) -> int:
        return round((time.perf_counter() - self.started) * 1000)


@dataclass
class RunContext:
    """Everything a pipeline component needs: the LLM, the execution tool and the event sink."""

    llm: LLMClient
    executor: Executor
    emit: Emit
    config: PipelineConfig = field(default_factory=PipelineConfig)
    stats: RunStats = field(default_factory=RunStats)

    def stage(self, stage_id: str, label: str) -> Stage:
        return Stage(self, stage_id, label)

    async def artifact(self, name: str, data: Any) -> None:
        await self.emit({"type": "artifact", "name": name, "data": data})

    async def execute(self, job: dict[str, Any]) -> dict[str, Any]:
        return await self.executor.run(job, self.config.exec_timeout_s)


class Stage:
    """Async context manager that reports a stage's lifecycle (and token usage) to the UI."""

    def __init__(self, ctx: RunContext, stage_id: str, label: str):
        self.ctx, self.id, self.label = ctx, stage_id, label
        self.detail, self.status = "", None
        self.tokens, self.models = 0, set()

    def note(self, detail: str, status: str | None = None) -> None:
        self.detail = detail
        if status:
            self.status = status

    def usage(self, u: Usage) -> None:
        self.tokens += u.input_tokens + u.output_tokens
        self.models.add(u.model)
        stats = self.ctx.stats
        stats.input_tokens += u.input_tokens
        stats.output_tokens += u.output_tokens
        stats.llm_calls += 1

    async def __aenter__(self) -> Stage:
        self._t0 = time.perf_counter()
        await self.ctx.emit({"type": "stage", "id": self.id, "label": self.label, "status": "running"})
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if isinstance(exc, asyncio.CancelledError):
            status, self.detail = "skipped", self.detail or "Stopped because another step failed."
        else:
            status = "failed" if exc else (self.status or "done")
            if exc and not self.detail:
                self.detail = str(exc)[:300]
        await self.ctx.emit({
            "type": "stage", "id": self.id, "label": self.label, "status": status,
            "detail": self.detail, "ms": round((time.perf_counter() - self._t0) * 1000),
            "tokens": self.tokens, "models": sorted(self.models),
        })


def parse_args(raw: str) -> list | None:
    """Parse an agent's ``*_args_json`` field; None unless it is a JSON array."""
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, list) else None


def harness_spec(spec: ProblemSpec) -> dict[str, Any]:
    """The subset of the spec the execution harness needs."""
    return {
        "entry": spec.entry,
        "kind": spec.kind,
        "params": [p.model_dump() for p in spec.params],
        "comparison": spec.comparison,
        "return_type": spec.return_type,
        "in_place_arg": spec.in_place_arg if spec.in_place_arg >= 0 else None,
    }
