import json
from datetime import UTC, datetime

import pytest

from agents.sentiment_aggregator import (
    DirectionalMemo,
    LabeledMemo,
    SentimentAggregationRequest,
    analyze,
)
from llm.client import StubClient


def _memo(
    direction: str = "bullish",
    confidence: int = 60,
    drivers: list[str] | None = None,
    summary: str = "テスト用メモ。",
) -> DirectionalMemo:
    return DirectionalMemo(
        direction=direction,  # type: ignore[arg-type]
        confidence=confidence,
        key_drivers=drivers or [],
        summary=summary,
    )


def _labeled(label: str, **kwargs: object) -> LabeledMemo:
    return LabeledMemo(label=label, memo=_memo(**kwargs))  # type: ignore[arg-type]


def _request(memos: list[LabeledMemo]) -> SentimentAggregationRequest:
    return SentimentAggregationRequest(
        horizon="open_today",
        as_of=datetime(2026, 5, 11, 7, 30, tzinfo=UTC),
        memos=memos,
    )


def _canned_responder(payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False)
    return lambda req: body


def test_analyze_returns_memo_from_stub():
    client = StubClient(
        responder=_canned_responder(
            {
                "direction": "bullish",
                "confidence": 72,
                "key_drivers": ["[central_bank] FOMC ハト派傾斜"],
                "summary": "中銀ハト派 + 国内ニュース弱気を加重し、寄付は上昇シナリオが優位。",
            }
        )
    )
    memo = analyze(
        _request(
            [
                _labeled("central_bank", direction="bullish", confidence=80),
                _labeled("domestic_news", direction="bearish", confidence=40),
            ]
        ),
        client=client,
    )
    assert isinstance(memo, DirectionalMemo)
    assert memo.direction == "bullish"
    assert memo.confidence == 72


def test_prompt_lists_each_labeled_memo():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        seen["system"] = req.system or ""
        return json.dumps(
            {
                "direction": "neutral",
                "confidence": 30,
                "key_drivers": [],
                "summary": "方向感拮抗のため判断保留。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze(
        _request(
            [
                _labeled("central_bank", direction="bullish", confidence=80,
                         drivers=["FOMC ハト派傾斜"]),
                _labeled("us_news", direction="bearish", confidence=50,
                         drivers=["米CPI上振れ"]),
            ]
        ),
        client=client,
    )
    user = seen["user"]
    assert "open_today" in user
    assert "label=central_bank" in user
    assert "label=us_news" in user
    assert "FOMC ハト派傾斜" in user
    assert "米CPI上振れ" in user
    assert "売買推奨は出力しない" in seen["system"]


def test_empty_memos_still_runs_and_marks_no_input():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        return json.dumps(
            {
                "direction": "neutral",
                "confidence": 10,
                "key_drivers": [],
                "summary": "入力メモなし。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    memo = analyze(_request([]), client=client)
    assert memo.direction == "neutral"
    assert "メモなし" in seen["user"]


def test_analyze_raises_on_invalid_json():
    client = StubClient(responder=lambda req: "garbage with no json")
    with pytest.raises(ValueError):
        analyze(_request([_labeled("x")]), client=client)
