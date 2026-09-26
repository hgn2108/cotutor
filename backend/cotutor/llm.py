"""LLM access behind a small interface so agents never depend on a vendor SDK directly.

* ``GeminiClient``  production client (structured JSON output, retries on rate limits).
* ``ScriptedLLM``   deterministic stand-in used by tests and offline demos.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

import httpx
from pydantic import BaseModel

Tier = Literal["smart", "fast"]
T = TypeVar("T", bound=BaseModel)


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    ms: float = 0.0


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    async def structured(
        self, *, agent: str, system: str, prompt: str, schema: type[T], tier: Tier = "smart",
        temperature: float = 0.2,
    ) -> tuple[T, Usage]: ...


class GeminiClient:
    """Structured-output Gemini client with a health-aware model router.

    Free-tier capacity flips per model from minute to minute (503 "high demand"). Each tier
    has a fallback chain; a model that just failed is put on a short cooldown shared by every
    session in the process, healthy models are tried first, and the chain is retried for a
    few rounds with backoff. Falling back to a weaker model is safe here because every agent
    output is verified by execution before anyone sees it. ``Usage.model`` reports the model
    that actually answered.
    """

    RETRYABLE = {429, 500, 502, 503, 504}
    COOLDOWN_S = 60.0
    _cooling_until: dict[str, float] = {}  # shared across instances on purpose

    def __init__(self, api_key: str, smart_models: list[str], fast_models: list[str],
                 rounds: int = 3, base_delay_s: float = 3.0, request_timeout_s: float = 45.0):
        from google import genai  # imported lazily so tests don't need credentials

        self._client = genai.Client(api_key=api_key)
        self._models = {"smart": smart_models, "fast": fast_models}
        self._rounds = rounds
        self._delay = base_delay_s
        # Under load a request can hang for minutes; better to fail fast and try another model.
        self._timeout = request_timeout_s

    async def _call(self, model: str, prompt: str, config):
        return await self._client.aio.models.generate_content(model=model, contents=prompt, config=config)

    def _ordered(self, chain: list[str]) -> list[str]:
        now = time.monotonic()
        healthy = [m for m in chain if self._cooling_until.get(m, 0) <= now]
        return healthy + [m for m in chain if m not in healthy]

    async def structured(self, *, agent, system, prompt, schema, tier="smart", temperature=0.2):
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        )
        last_error = "no models configured"
        for round_no in range(self._rounds):
            if round_no:
                await asyncio.sleep(self._delay * round_no + random.random() * self._delay)
            for model in self._ordered(self._models[tier]):
                start = time.perf_counter()
                try:
                    resp = await asyncio.wait_for(self._call(model, prompt, config), self._timeout)
                    parsed = resp.parsed if isinstance(resp.parsed, schema) else None
                    if parsed is None:
                        parsed = schema.model_validate_json(resp.text or "")
                except errors.APIError as exc:
                    if exc.code not in self.RETRYABLE:
                        raise LLMError(f"{agent}: Gemini error {exc.code}: {exc.message}") from exc
                    self._cooling_until[model] = time.monotonic() + self.COOLDOWN_S
                    last_error = f"{model} returned {exc.code}"
                    continue
                except ValueError:  # malformed structured output; another try usually fixes it
                    last_error = f"{model} returned invalid JSON"
                    continue
                except (httpx.TransportError, TimeoutError, ConnectionError) as exc:
                    # Dropped connections and timeouts behave like a momentary overload.
                    self._cooling_until[model] = time.monotonic() + self.COOLDOWN_S / 4
                    last_error = f"{model}: {type(exc).__name__}"
                    continue
                self._cooling_until.pop(model, None)
                meta = resp.usage_metadata
                return parsed, Usage(
                    model=model,
                    input_tokens=(meta.prompt_token_count or 0) if meta else 0,
                    output_tokens=(meta.candidates_token_count or 0) if meta else 0,
                    ms=(time.perf_counter() - start) * 1000,
                )
        raise LLMError(f"{agent}: Gemini is overloaded right now (last: {last_error}). "
                       "Please try again in a minute.")


class ScriptedLLM:
    """Returns pre-baked responses per agent, in order. Records every prompt it receives."""

    def __init__(self, script: dict[str, list[BaseModel]]):
        self._script = {k: list(v) for k, v in script.items()}
        self.calls: dict[str, list[str]] = defaultdict(list)

    async def structured(self, *, agent, system, prompt, schema, tier="smart", temperature=0.2):
        self.calls[agent].append(prompt)
        queue = self._script.get(agent)
        if not queue:
            raise LLMError(f"ScriptedLLM has no response left for agent '{agent}'")
        value = queue.pop(0)
        if not isinstance(value, schema):
            value = schema.model_validate(value.model_dump())
        await asyncio.sleep(0)
        return value, Usage(model="scripted", input_tokens=len(prompt) // 4, output_tokens=0)
