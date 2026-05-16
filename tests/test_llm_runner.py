import json

import pytest
from pydantic import BaseModel, ValidationError

from config import LLMSettings, Settings, reset_settings, set_settings
from llm.client import StubClient
from llm.runner import run_json_agent


class _Memo(BaseModel):
    direction: str
    confidence: int


@pytest.fixture(autouse=True)
def _reset_settings_around_each_test():
    reset_settings()
    yield
    reset_settings()


def test_run_json_agent_returns_validated_model():
    client = StubClient(
        responder=lambda req: json.dumps({"direction": "bullish", "confidence": 65})
    )
    memo = run_json_agent(
        system="sys",
        user="u",
        schema=_Memo,
        client=client,
    )
    assert isinstance(memo, _Memo)
    assert memo.direction == "bullish"
    assert memo.confidence == 65


def test_run_json_agent_post_process_runs_before_validation():
    client = StubClient(
        responder=lambda req: json.dumps({"direction": "bullish"})  # confidence 欠
    )
    memo = run_json_agent(
        system="sys",
        user="u",
        schema=_Memo,
        client=client,
        post_process=lambda payload: {**payload, "confidence": 50},
    )
    assert memo.confidence == 50


def test_run_json_agent_invalid_json_raises():
    client = StubClient(responder=lambda req: "no json here")
    with pytest.raises(ValueError):
        run_json_agent(system="sys", user="u", schema=_Memo, client=client)


def test_run_json_agent_schema_violation_raises():
    client = StubClient(responder=lambda req: json.dumps({"direction": "bullish"}))
    with pytest.raises(ValidationError):
        run_json_agent(system="sys", user="u", schema=_Memo, client=client)


def test_runner_uses_settings_defaults_for_tokens_and_temperature():
    seen: dict[str, object] = {}

    def responder(req):
        seen["max_tokens"] = req.max_tokens
        seen["temperature"] = req.temperature
        return json.dumps({"direction": "neutral", "confidence": 10})

    set_settings(
        Settings(llm=LLMSettings(default_max_tokens=512, default_temperature=0.7))
    )
    client = StubClient(responder=responder)
    run_json_agent(system="sys", user="u", schema=_Memo, client=client)
    assert seen["max_tokens"] == 512
    assert seen["temperature"] == 0.7


def test_runner_explicit_args_override_settings():
    seen: dict[str, object] = {}

    def responder(req):
        seen["max_tokens"] = req.max_tokens
        seen["temperature"] = req.temperature
        seen["model"] = req.model
        return json.dumps({"direction": "neutral", "confidence": 10})

    set_settings(Settings(llm=LLMSettings(default_max_tokens=512)))
    client = StubClient(responder=responder)
    run_json_agent(
        system="sys",
        user="u",
        schema=_Memo,
        client=client,
        max_tokens=2048,
        temperature=0.2,
        model="claude-haiku-4-5",
    )
    assert seen["max_tokens"] == 2048
    assert seen["temperature"] == 0.2
    assert seen["model"] == "claude-haiku-4-5"


def test_runner_passes_system_and_user_through():
    seen: dict[str, object] = {}

    def responder(req):
        seen["system"] = req.system
        seen["user"] = req.messages[-1].content
        return json.dumps({"direction": "neutral", "confidence": 10})

    client = StubClient(responder=responder)
    run_json_agent(system="SYS-PROMPT", user="USER-MSG", schema=_Memo, client=client)
    assert seen["system"] == "SYS-PROMPT"
    assert seen["user"] == "USER-MSG"
