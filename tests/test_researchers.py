import json
from datetime import UTC, datetime

import pytest

from agents.researchers import (
    BEAR_SYSTEM_PROMPT,
    BULL_SYSTEM_PROMPT,
    DirectionalMemo,
    LabeledMemo,
    ResearcherRequest,
    analyze_bear,
    analyze_bull,
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


def _request(
    memos: list[LabeledMemo] | None = None,
    opposing: DirectionalMemo | None = None,
) -> ResearcherRequest:
    return ResearcherRequest(
        horizon="open_today",
        as_of=datetime(2026, 5, 11, 7, 30, tzinfo=UTC),
        memos=memos or [],
        opposing_memo=opposing,
    )


def _canned_responder(payload: dict[str, object]):
    body = json.dumps(payload, ensure_ascii=False)
    return lambda req: body


def test_bull_returns_memo_from_stub():
    client = StubClient(
        responder=_canned_responder(
            {
                "direction": "bullish",
                "confidence": 65,
                "key_drivers": ["FOMC ハト派傾斜"],
                "summary": "中銀ハト派で上昇シナリオが優位。",
            }
        )
    )
    memo = analyze_bull(
        _request([_labeled("central_bank", direction="bullish", confidence=80)]),
        client=client,
    )
    assert isinstance(memo, DirectionalMemo)
    assert memo.direction == "bullish"
    assert memo.confidence == 65


def test_bear_returns_memo_from_stub():
    client = StubClient(
        responder=_canned_responder(
            {
                "direction": "bearish",
                "confidence": 60,
                "key_drivers": ["米CPI上振れ"],
                "summary": "インフレ再加速で利下げ後ずれ、下落シナリオが優位。",
            }
        )
    )
    memo = analyze_bear(
        _request([_labeled("us_news", direction="bearish", confidence=70)]),
        client=client,
    )
    assert memo.direction == "bearish"
    assert memo.confidence == 60


def test_bull_and_bear_send_different_system_prompts():
    seen_systems: list[str] = []

    def responder(req):
        seen_systems.append(req.system or "")
        return json.dumps(
            {
                "direction": "neutral",
                "confidence": 20,
                "key_drivers": [],
                "summary": "材料乏しく方向感なし。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze_bull(_request(), client=client)
    analyze_bear(_request(), client=client)
    assert seen_systems[0] == BULL_SYSTEM_PROMPT
    assert seen_systems[1] == BEAR_SYSTEM_PROMPT
    assert "Bull Researcher" in seen_systems[0]
    assert "Bear Researcher" in seen_systems[1]
    # bearish 禁止 / bullish 禁止が両プロンプトに明示される
    assert "bearish は返さない" in seen_systems[0]
    assert "bullish は返さない" in seen_systems[1]


def test_opposing_memo_is_rendered_in_prompt():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        return json.dumps(
            {
                "direction": "bullish",
                "confidence": 55,
                "key_drivers": ["米株先物堅調"],
                "summary": "弱気側の利下げ後ずれ懸念は米株堅調で限定的、強気シナリオ維持。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    bear_memo = _memo(
        direction="bearish",
        confidence=70,
        drivers=["米CPI上振れ"],
        summary="インフレ再加速で利下げ後ずれ。",
    )
    analyze_bull(_request(opposing=bear_memo), client=client)
    user = seen["user"]
    assert "opposing_memo" in user
    assert "米CPI上振れ" in user
    assert "direction=bearish" in user


def test_initial_round_marks_no_opposing():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        return json.dumps(
            {
                "direction": "neutral",
                "confidence": 20,
                "key_drivers": [],
                "summary": "材料乏しく初回判断保留。",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze_bear(_request(), client=client)
    assert "初回ターン" in seen["user"]


def test_prompt_lists_each_labeled_memo():
    seen: dict[str, str] = {}

    def responder(req):
        seen["user"] = req.messages[-1].content
        return json.dumps(
            {
                "direction": "bullish",
                "confidence": 50,
                "key_drivers": [],
                "summary": "...",
            },
            ensure_ascii=False,
        )

    client = StubClient(responder=responder)
    analyze_bull(
        _request(
            [
                _labeled("central_bank", drivers=["FOMC ハト派傾斜"]),
                _labeled("technical", drivers=["200日線上抜け"]),
            ]
        ),
        client=client,
    )
    user = seen["user"]
    assert "label=central_bank" in user
    assert "label=technical" in user
    assert "FOMC ハト派傾斜" in user
    assert "200日線上抜け" in user


def test_invalid_json_raises():
    client = StubClient(responder=lambda req: "no json here")
    with pytest.raises(ValueError):
        analyze_bull(_request(), client=client)
