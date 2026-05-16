import pytest

from llm.client import (
    CompletionRequest,
    Message,
    StubClient,
    get_client,
    parse_json_response,
)


def _req(text: str) -> CompletionRequest:
    return CompletionRequest(messages=[Message(role="user", content=text)])


def test_stub_client_default_responder_echoes_user():
    result = StubClient().complete(_req("hello world"))
    assert result.content.startswith("[stub] hello world")
    assert result.stop_reason == "end_turn"
    assert result.model == "stub"


def test_stub_client_custom_responder():
    client = StubClient(responder=lambda req: f"got {len(req.messages)} msgs")
    result = client.complete(_req("anything"))
    assert result.content == "got 1 msgs"


def test_get_client_without_api_key_returns_stub(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(get_client(), StubClient)


def test_parse_json_response_plain():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_response_strips_fences():
    assert parse_json_response('```json\n{"a": 2}\n```') == {"a": 2}


def test_parse_json_response_strips_unlabeled_fences():
    assert parse_json_response('```\n{"a": 3}\n```') == {"a": 3}


def test_parse_json_response_extracts_from_prose():
    assert parse_json_response('説明文。 {"a": 4} ありがとう。') == {"a": 4}


def test_parse_json_response_raises_on_no_json():
    with pytest.raises(ValueError):
        parse_json_response("no json here")
