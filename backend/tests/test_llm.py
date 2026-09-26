"""The Gemini client routes around overloaded models."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from cotutor.llm import GeminiClient, LLMError
from cotutor.schemas import Param

OK = Param(name="x", type="int")


class FakeGemini(GeminiClient):
    def __init__(self, behavior: dict[str, list], rounds: int = 2):
        super().__init__("test-key", ["smart-a", "smart-b"], ["fast-a"], rounds=rounds, base_delay_s=0,
                         request_timeout_s=0.05)
        self.behavior = behavior
        self.calls: list[str] = []

    async def _call(self, model, prompt, config):
        self.calls.append(model)
        outcome = self.behavior[model].pop(0)
        if outcome == "hang":
            await asyncio.sleep(10)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, int):
            raise errors.APIError(outcome, {"error": {"message": "busy"}})
        return SimpleNamespace(parsed=outcome, text="", usage_metadata=None)


@pytest.fixture(autouse=True)
def reset_cooldowns():
    GeminiClient._cooling_until.clear()


async def test_falls_back_to_next_model_on_overload():
    llm = FakeGemini({"smart-a": [503], "smart-b": [OK]})
    value, usage = await llm.structured(agent="t", system="", prompt="", schema=Param)
    assert value == OK and usage.model == "smart-b"
    assert llm.calls == ["smart-a", "smart-b"]


async def test_overloaded_model_is_skipped_by_later_calls():
    llm = FakeGemini({"smart-a": [503], "smart-b": [OK, OK]})
    await llm.structured(agent="t", system="", prompt="", schema=Param)
    await llm.structured(agent="t", system="", prompt="", schema=Param)
    assert llm.calls == ["smart-a", "smart-b", "smart-b"]  # smart-a is cooling down


async def test_retries_the_chain_in_later_rounds():
    llm = FakeGemini({"smart-a": [503, 503], "smart-b": [503, OK]})
    value, _ = await llm.structured(agent="t", system="", prompt="", schema=Param)
    assert value == OK and len(llm.calls) == 4


async def test_non_retryable_error_fails_fast():
    llm = FakeGemini({"smart-a": [400]})
    with pytest.raises(LLMError, match="400"):
        await llm.structured(agent="t", system="", prompt="", schema=Param)
    assert llm.calls == ["smart-a"]


async def test_gives_up_when_every_model_stays_down():
    llm = FakeGemini({"fast-a": [503, 429]})
    with pytest.raises(LLMError, match="overloaded"):
        await llm.structured(agent="t", system="", prompt="", schema=Param, tier="fast")


async def test_dropped_connection_fails_over():
    llm = FakeGemini({"smart-a": [httpx.RemoteProtocolError("disconnected")], "smart-b": [OK]})
    value, usage = await llm.structured(agent="t", system="", prompt="", schema=Param)
    assert usage.model == "smart-b"


async def test_hung_request_times_out_and_fails_over():
    llm = FakeGemini({"smart-a": ["hang"], "smart-b": [OK]})
    _, usage = await llm.structured(agent="t", system="", prompt="", schema=Param)
    assert usage.model == "smart-b"
