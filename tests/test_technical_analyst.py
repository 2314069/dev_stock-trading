import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agents.technical_analyst import (
    DirectionalMemo,
    TechnicalAnalysisRequest,
    TechnicalIndicators,
    analyze,
)
from data.jpx import FuturesBar
from llm.client import StubClient


def _indicators(**overrides: float | str | None) -> TechnicalIndicators:
    base: dict[str, object] = {
        "last_price": 38500.0,
        "prev_close": 38400.0,
        "sma_5": 38450.0,
        "sma_25": 38200.0,
        "sma_75": 37900.0,
        "sma_200": 37000.0,
        "rsi_14": 58.0,
        "macd": 25.0,
        "macd_signal": 18.0,
        "bollinger_width": 320.0,
        "atr_14": 280.0,
        "ichimoku_cloud_position": "above",
        "overnight_return": 0.003,
    }
    base.update(overrides)
    return TechnicalIndicators(**base)  # type: ignore[arg-type]


def _request(
    indicators: TechnicalIndicators | None = None,
    bars: list[FuturesBar] | None = None,
) -> TechnicalAnalysisRequest:
    return TechnicalAnalysisRequest(
        horizon="close_today",
        as_of=datetime(2026, 5, 11, 0, 30, tzinfo=UTC),
        symbol="NK225M6",
        indicators=indicators or _indicators(),
        recent_bars=bars or [],
    )


def _canned_responder(payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False)
    return lambda req: body


def test_analyze_returns_memo_from_stub():
    client = StubClient(
        responder=_canned_responder(
            {
                "direction": "bullish",
                "confidence": 70,
                "key_drivers": ["MACD 強気クロス", "200日線上抜け"],
                "summary": "中期トレンド回復、終値は上方向シナリオが優位。",
            }
        )
    )
    memo = analyze(_request(), client=client)
    assert isinstance(memo, DirectionalMemo)
    assert memo.direction == "bullish"
    assert memo.confidence == 70
    assert "MACD 強気クロス" in memo.key_drivers


def test_analyze_handles_json_fences():
    payload = json.dumps(
        {
            "direction": "neutral",
            "confidence": 35,
            "key_drivers": [],
            "summary": "シグナル乏しく方向感なし。",
        },
        ensure_ascii=False,
    )
    client = StubClient(responder=lambda req: f"```json\n{payload}\n```")
    memo = analyze(_request(), client=client)
    assert memo.direction == "neutral"
    assert memo.confidence == 35


def test_prompt_contains_horizon_symbol_and_indicators():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        seen["system"] = req.system or ""
        return json.dumps(
            {
                "direction": "bearish",
                "confidence": 55,
                "key_drivers": ["RSI 過熱"],
                "summary": "短期過熱で押し目試しのシナリオ。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze(
        _request(
            indicators=_indicators(rsi_14=78.0),
            bars=[
                FuturesBar(
                    timestamp=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
                    open=38400, high=38520, low=38380, close=38500, volume=1234,
                ),
            ],
        ),
        client=client,
    )
    user = seen["user"]
    assert "NK225M6" in user
    assert "close_today" in user
    assert "78.00" in user  # RSI が整形されて含まれる
    assert "2026-05-11" in user  # 直近足のタイムスタンプ
    assert "売買推奨は出力しない" in seen["system"]


def test_prompt_marks_missing_indicators_as_none():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        return json.dumps(
            {
                "direction": "neutral",
                "confidence": 20,
                "key_drivers": [],
                "summary": "指標欠損のため判定保留。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze(
        _request(
            indicators=_indicators(
                rsi_14=None,
                macd=None,
                macd_signal=None,
                ichimoku_cloud_position=None,
            ),
        ),
        client=client,
    )
    # 欠損指標は "None" として表示され、エージェントが「判断材料に使わない」と判別できる
    assert "RSI(14)=None" in seen["user"]
    assert "雲との位置=None" in seen["user"]


def test_analyze_raises_on_invalid_json():
    client = StubClient(responder=lambda req: "garbage with no json")
    with pytest.raises(ValueError):
        analyze(_request(), client=client)


def test_indicators_validate_rsi_bounds():
    with pytest.raises(ValidationError):
        TechnicalIndicators(last_price=1.0, prev_close=1.0, rsi_14=150.0)
