import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agents.portfolio_manager import (
    PortfolioPlan,
    PortfolioRequest,
    synthesize,
)
from agents.types import DirectionalMemo, DirectionProbabilities, LabeledMemo
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


def _request(
    memos: list[LabeledMemo] | None = None,
    bull: DirectionalMemo | None = None,
    bear: DirectionalMemo | None = None,
) -> PortfolioRequest:
    return PortfolioRequest(
        horizon="open_today",
        as_of=datetime(2026, 5, 11, 7, 30, tzinfo=UTC),
        symbol="NK225M6",
        memos=memos or [],
        bull_memo=bull,
        bear_memo=bear,
    )


def _canned_payload(
    direction: str = "bullish",
    probs: tuple[float, float, float] = (0.6, 0.3, 0.1),
    confidence: int = 65,
    drivers: list[str] | None = None,
    scenario: str = "強気優位。",
    bull_case: str = "中銀ハト派が支援。",
    bear_case: str = "上値追いには利下げ後ずれ懸念が抵抗。",
) -> dict[str, object]:
    b, n, s = probs
    return {
        "direction": direction,
        "direction_probabilities": {"bullish": b, "neutral": n, "bearish": s},
        "confidence": confidence,
        "top_drivers": drivers or ["FOMC ハト派傾斜", "200日線上抜け"],
        "scenario": scenario,
        "bull_case": bull_case,
        "bear_case": bear_case,
    }


def _canned_responder(payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False)
    return lambda req: body


def test_synthesize_returns_plan_from_stub():
    client = StubClient(responder=_canned_responder(_canned_payload()))
    plan = synthesize(
        _request(
            memos=[_labeled("sentiment", direction="bullish", confidence=70)],
            bull=_memo(direction="bullish", confidence=70, drivers=["FOMC ハト派傾斜"]),
            bear=_memo(direction="bearish", confidence=55, drivers=["米CPI上振れ"]),
        ),
        client=client,
    )
    assert isinstance(plan, PortfolioPlan)
    assert plan.direction == "bullish"
    assert plan.confidence == 65
    assert plan.direction_probabilities.bullish == 0.6
    assert plan.top_drivers == ["FOMC ハト派傾斜", "200日線上抜け"]
    assert plan.bull_case
    assert plan.bear_case


def test_horizon_is_set_from_request_not_llm():
    payload = _canned_payload()
    # LLM 出力に horizon が含まれていても、最終的には req.horizon が優先される
    payload["horizon"] = "close_today"  # 意図的に不一致な値
    client = StubClient(responder=_canned_responder(payload))
    plan = synthesize(_request(), client=client)
    assert plan.horizon == "open_today"


def test_prompt_renders_memos_and_both_sides():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        seen["system"] = req.system or ""
        return json.dumps(_canned_payload(), ensure_ascii=False)

    client = StubClient(responder=responder)
    synthesize(
        _request(
            memos=[
                _labeled("sentiment", direction="bullish", confidence=70,
                         drivers=["FOMC ハト派傾斜"]),
                _labeled("technical", direction="neutral", confidence=40,
                         drivers=["MACD シグナル混在"]),
            ],
            bull=_memo(direction="bullish", confidence=70, drivers=["米株先物堅調"]),
            bear=_memo(direction="bearish", confidence=55, drivers=["米CPI上振れ"]),
        ),
        client=client,
    )
    user = seen["user"]
    assert "NK225M6" in user
    assert "open_today" in user
    assert "label=sentiment" in user
    assert "label=technical" in user
    assert "Bull Researcher" in user
    assert "Bear Researcher" in user
    assert "FOMC ハト派傾斜" in user
    assert "米株先物堅調" in user
    assert "米CPI上振れ" in user
    assert "売買推奨は出力しない" in seen["system"]


def test_missing_bull_or_bear_marked_as_absent_in_prompt():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        return json.dumps(_canned_payload(bull_case="", bear_case=""), ensure_ascii=False)

    client = StubClient(responder=responder)
    synthesize(_request(), client=client)
    assert "Bull Researcher: 入力なし" in seen["user"]
    assert "Bear Researcher: 入力なし" in seen["user"]


def test_probabilities_validate_sum_to_one():
    # Pydantic 側で和が ~1.0 を超える分布を拒否することを確認
    with pytest.raises(ValidationError):
        DirectionProbabilities(bullish=0.7, neutral=0.7, bearish=0.0)


def test_synthesize_raises_when_llm_returns_invalid_probabilities():
    bad = _canned_payload(probs=(0.7, 0.7, 0.7))
    client = StubClient(responder=_canned_responder(bad))
    with pytest.raises(ValidationError):
        synthesize(_request(), client=client)


def test_top_drivers_capped_to_5():
    bad = _canned_payload(drivers=["a", "b", "c", "d", "e", "f"])
    client = StubClient(responder=_canned_responder(bad))
    with pytest.raises(ValidationError):
        synthesize(_request(), client=client)


def test_invalid_json_raises():
    client = StubClient(responder=lambda req: "garbage")
    with pytest.raises(ValueError):
        synthesize(_request(), client=client)
