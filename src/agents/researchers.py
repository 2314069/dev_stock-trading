"""Researcher Bull / Bear エージェント (F-08)。

News / Technical / Sentiment Aggregator から集まった `LabeledMemo` 群を入力に、
担当サイド（強気 = Bull、弱気 = Bear）から見たシナリオを構築する。各エージェントは
シングルショット呼び出しのみを担い、マルチターン議論のオーケストレーションは
`src/graph/` (LangGraph) の責務として分離する。

反論ターン用に `opposing_memo` を任意で受け取り、相手側の前回出力に直接反論する形で
プロンプトを構築する（None なら初回ターン扱い）。

役割上の制約（プロンプトで指示）:
- Bull は強気側の最も説得力ある根拠を構築する。データが弱気を強く支持する場合は無理に
  bullish と返さず、neutral + 低 confidence で正直に返す。bearish は返さない。
- Bear はその鏡像。
- どちらも売買推奨は出さず、入力に無い数値・固有名詞・銘柄名は創作しない。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from agents.types import DirectionalMemo, Horizon, LabeledMemo
from llm.client import (
    CompletionRequest,
    LLMClient,
    Message,
    get_client,
    parse_json_response,
)


class ResearcherRequest(BaseModel):
    horizon: Horizon
    as_of: datetime
    memos: list[LabeledMemo] = Field(default_factory=list)
    opposing_memo: DirectionalMemo | None = None


BULL_SYSTEM_PROMPT = """\
あなたは日経平均先物の強気シナリオを担当する Bull Researcher です。
与えられたメモ群から「上昇する根拠」を抽出し、最も説得力のある強気ケースを構築します。

制約:
- 売買推奨は出力しない（統計的シナリオ提示に限定）。
- 入力メモに無い数値・固有名詞・銘柄名を創作しない。
- 強気側の視点に立つが、データが弱気を強く支持する場合は無理に bullish と返さず、
  neutral + 低 confidence で正直に返す。direction に bearish は返さない。
- opposing_memo（弱気側の前回主張）がある場合は、その論点に**直接反論**して論理を再構築する。
  反論できない論点があれば summary に正直にその旨を書く。
- key_drivers には強気を支える観点を入れる（最大 5 件、入力メモまたは opposing_memo に
  根拠を持つもののみ）。

出力は厳密な JSON のみ。前後に説明文・フェンスを付けない。スキーマ:
{
  "direction": "bullish" | "neutral",
  "confidence": 0-100 の整数,
  "key_drivers": ["強気を支える観点", ...] (最大 5 件),
  "summary": "100 字程度の強気シナリオ"
}
"""

BEAR_SYSTEM_PROMPT = """\
あなたは日経平均先物の弱気シナリオを担当する Bear Researcher です。
与えられたメモ群から「下落する根拠」を抽出し、最も説得力のある弱気ケースを構築します。

制約:
- 売買推奨は出力しない（統計的シナリオ提示に限定）。
- 入力メモに無い数値・固有名詞・銘柄名を創作しない。
- 弱気側の視点に立つが、データが強気を強く支持する場合は無理に bearish と返さず、
  neutral + 低 confidence で正直に返す。direction に bullish は返さない。
- opposing_memo（強気側の前回主張）がある場合は、その論点に**直接反論**して論理を再構築する。
  反論できない論点があれば summary に正直にその旨を書く。
- key_drivers には弱気を支える観点を入れる（最大 5 件、入力メモまたは opposing_memo に
  根拠を持つもののみ）。

出力は厳密な JSON のみ。前後に説明文・フェンスを付けない。スキーマ:
{
  "direction": "bearish" | "neutral",
  "confidence": 0-100 の整数,
  "key_drivers": ["弱気を支える観点", ...] (最大 5 件),
  "summary": "100 字程度の弱気シナリオ"
}
"""


def _format_memo(idx: int, lm: LabeledMemo) -> str:
    drivers = ", ".join(lm.memo.key_drivers) if lm.memo.key_drivers else "-"
    return (
        f"[{idx}] label={lm.label} direction={lm.memo.direction} "
        f"confidence={lm.memo.confidence}\n"
        f"     key_drivers: {drivers}\n"
        f"     summary: {lm.memo.summary}"
    )


def _format_memos(memos: list[LabeledMemo]) -> str:
    if not memos:
        return "(メモなし)"
    return "\n".join(_format_memo(i, m) for i, m in enumerate(memos))


def _format_opposing(memo: DirectionalMemo | None) -> str:
    if memo is None:
        return "(初回ターン: 反論対象なし)"
    drivers = ", ".join(memo.key_drivers) if memo.key_drivers else "-"
    return (
        f"direction={memo.direction} confidence={memo.confidence}\n"
        f"key_drivers: {drivers}\n"
        f"summary: {memo.summary}"
    )


def _build_user_message(req: ResearcherRequest) -> str:
    return (
        f"対象ホライゾン: {req.horizon}\n"
        f"基準時刻 (as_of): {req.as_of.isoformat()}\n"
        f"入力メモ件数: {len(req.memos)}\n\n"
        f"メモ一覧:\n{_format_memos(req.memos)}\n\n"
        f"相手側の前回主張 (opposing_memo):\n{_format_opposing(req.opposing_memo)}\n\n"
        "上記から担当サイドのシナリオを上記スキーマの JSON のみで返してください。"
    )


def _run(
    req: ResearcherRequest,
    *,
    system_prompt: str,
    client: LLMClient | None,
    model: str | None,
) -> DirectionalMemo:
    client = client or get_client()
    completion_kwargs: dict[str, object] = {
        "system": system_prompt,
        "messages": [Message(role="user", content=_build_user_message(req))],
        "max_tokens": 1024,
        "temperature": 0.0,
    }
    if model is not None:
        completion_kwargs["model"] = model
    result = client.complete(CompletionRequest(**completion_kwargs))  # type: ignore[arg-type]
    payload = parse_json_response(result.content)
    return DirectionalMemo.model_validate(payload)


def analyze_bull(
    req: ResearcherRequest,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
) -> DirectionalMemo:
    """Bull Researcher を 1 回実行する。"""
    return _run(req, system_prompt=BULL_SYSTEM_PROMPT, client=client, model=model)


def analyze_bear(
    req: ResearcherRequest,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
) -> DirectionalMemo:
    """Bear Researcher を 1 回実行する。"""
    return _run(req, system_prompt=BEAR_SYSTEM_PROMPT, client=client, model=model)


__all__ = [
    "BEAR_SYSTEM_PROMPT",
    "BULL_SYSTEM_PROMPT",
    "DirectionalMemo",
    "Horizon",
    "LabeledMemo",
    "ResearcherRequest",
    "analyze_bear",
    "analyze_bull",
]
