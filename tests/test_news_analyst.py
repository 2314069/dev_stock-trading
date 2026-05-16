import json
from datetime import UTC, datetime

import pytest

from agents.news_analyst import (
    DirectionalMemo,
    NewsAnalysisRequest,
    NewsItem,
    analyze,
)
from llm.client import StubClient


def _news(headline: str, sentiment: float = 0.0, impact: str = "Medium") -> NewsItem:
    return NewsItem(
        timestamp=datetime(2026, 5, 11, 3, 0, tzinfo=UTC),
        source="Reuters",
        headline=headline,
        impact=impact,  # type: ignore[arg-type]
        sentiment=sentiment,
    )


def _request(news: list[NewsItem]) -> NewsAnalysisRequest:
    return NewsAnalysisRequest(
        horizon="open_today",
        as_of=datetime(2026, 5, 11, 7, 30, tzinfo=UTC),
        news=news,
    )


def _canned_responder(payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False)
    return lambda req: body


def test_analyze_returns_memo_from_stub():
    client = StubClient(
        responder=_canned_responder(
            {
                "direction": "bullish",
                "confidence": 65,
                "key_drivers": ["FOMC ハト派傾斜"],
                "summary": "米金利低下と円安進行で寄付は上昇方向。",
            }
        )
    )
    memo = analyze(
        _request([_news("FOMC ハト派傾斜", sentiment=0.6, impact="High")]),
        client=client,
    )
    assert isinstance(memo, DirectionalMemo)
    assert memo.direction == "bullish"
    assert memo.confidence == 65
    assert memo.key_drivers == ["FOMC ハト派傾斜"]


def test_analyze_handles_json_fences():
    payload = json.dumps(
        {
            "direction": "neutral",
            "confidence": 30,
            "key_drivers": [],
            "summary": "材料乏しく方向感なし。",
        },
        ensure_ascii=False,
    )
    client = StubClient(responder=lambda req: f"```json\n{payload}\n```")
    memo = analyze(_request([]), client=client)
    assert memo.direction == "neutral"
    assert memo.confidence == 30


def test_analyze_passes_horizon_and_news_to_prompt():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        seen["system"] = req.system or ""
        return json.dumps(
            {
                "direction": "bearish",
                "confidence": 55,
                "key_drivers": ["米CPI上振れ"],
                "summary": "利下げ後ずれ観測で軟調。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze(
        _request([_news("米CPI上振れ", sentiment=-0.4, impact="High")]),
        client=client,
    )
    assert "open_today" in seen["user"]
    assert "米CPI上振れ" in seen["user"]
    assert "売買推奨は出力しない" in seen["system"]


def test_analyze_raises_on_invalid_json():
    client = StubClient(responder=lambda req: "garbage with no json")
    with pytest.raises(ValueError):
        analyze(_request([]), client=client)


def test_analyze_raises_on_invalid_schema():
    client = StubClient(
        responder=_canned_responder({"direction": "sideways", "confidence": 50})
    )
    with pytest.raises(Exception):  # pydantic ValidationError
        analyze(_request([]), client=client)
