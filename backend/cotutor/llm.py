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
    RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, smart_model: str, fast_model: str, max_attempts: int = 4):
        from google import genai  # imported lazily so tests don't need credentials

        self._client = genai.Client(api_key=api_key)
        self._models = {"smart": smart_model, "fast": fast_model}
        self._max_attempts = max_attempts

    async def structured(self, *, agent, system, prompt, schema, tier="smart", temperature=0.2):
        from google.genai import errors, types

        model = self._models[tier]
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        )
        for attempt in range(1, self._max_attempts + 1):
            start = time.perf_counter()
            try:
                resp = await self._client.aio.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                parsed = resp.parsed if isinstance(resp.parsed, schema) else None
                if parsed is None:
                    parsed = schema.model_validate_json(resp.text or "")
                meta = resp.usage_metadata
                usage = Usage(
                    model=model,
                    input_tokens=(meta.prompt_token_count or 0) if meta else 0,
                    output_tokens=(meta.candidates_token_count or 0) if meta else 0,
                    ms=(time.perf_counter() - start) * 1000,
                )
                return parsed, usage
            except errors.APIError as exc:
                if exc.code not in self.RETRYABLE or attempt == self._max_attempts:
                    raise LLMError(f"{agent}: Gemini error {exc.code}: {exc.message}") from exc
            except ValueError as exc:  # malformed JSON; retrying usually fixes it
                if attempt == self._max_attempts:
                    raise LLMError(f"{agent}: invalid structured output") from exc
            await asyncio.sleep(min(20, 2**attempt) + random.random())
        raise LLMError(f"{agent}: exhausted retries")


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
