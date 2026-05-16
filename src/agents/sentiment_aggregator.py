"""Sentiment Aggregator エージェント (F-08)。

複数の `DirectionalMemo`（典型的にはカテゴリ別 / ソース別に走らせた News Analyst の出力）を
1 つの方向性メモに集約する。集約は LLM ベースで、単純な加重多数決ではなく:
- 各メモの confidence と label（出所文脈）を加味
- メモ間の矛盾を検出して summary に明示
- 強い矛盾時は neutral + 低 confidence で返す
を担う。

出力スキーマは他エージェントと同じ `DirectionalMemo`。Portfolio Manager から見ると
個別 News Analyst と同列のシグナル源として扱える。
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


class SentimentAggregationRequest(BaseModel):
    horizon: Horizon
    as_of: datetime
    memos: list[LabeledMemo] = Field(default_factory=list)


SYSTEM_PROMPT = """\
あなたは日経平均先物のセンチメント統合を担当するアナリストです。
複数の方向性メモ（カテゴリ別 / ソース別の News Analyst 出力など）を受け取り、
指定ホライゾンに向けた 1 つの統合メモに集約します。

制約:
- 売買推奨は出力しない（統計的シナリオ提示に限定）。
- 入力メモに無い情報・固有名詞・数値を創作しない。
- 集約方針:
  - 各メモの direction を、confidence と label の重要度で加重して総合判断する。
  - 中央銀行・公式発表・取引所開示 (label に "central_bank" / "official" / "exchange" を含む)
    は一般ニュースより重視する。
  - 多数の bullish と少数の高 confidence な bearish のように方向が割れる場合は、その乖離
    そのものを summary に書く（無理に統合しない）。
  - メモが極端に少ない・全てが低 confidence・方向が拮抗する場合は neutral + 低 confidence。
- key_drivers には統合判断に効いたメモの label と要旨を入れる（最大 5 件、
  入力に存在する label から選ぶ）。

出力は厳密な JSON のみ。前後に説明文・フェンスを付けない。スキーマ:
{
  "direction": "bullish" | "neutral" | "bearish",
  "confidence": 0-100 の整数,
  "key_drivers": ["[label] 要旨", ...] (最大 5 件),
  "summary": "100 字程度の統合方向性メモ"
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


def _build_user_message(req: SentimentAggregationRequest) -> str:
    return (
        f"対象ホライゾン: {req.horizon}\n"
        f"基準時刻 (as_of): {req.as_of.isoformat()}\n"
        f"集約対象メモ件数: {len(req.memos)}\n\n"
        f"メモ一覧:\n{_format_memos(req.memos)}\n\n"
        "上記から統合方向性メモを上記スキーマの JSON のみで返してください。"
    )


def analyze(
    req: SentimentAggregationRequest,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
) -> DirectionalMemo:
    """Sentiment Aggregator を 1 回実行する。"""
    client = client or get_client()
    completion_kwargs: dict[str, object] = {
        "system": SYSTEM_PROMPT,
        "messages": [Message(role="user", content=_build_user_message(req))],
        "max_tokens": 1024,
        "temperature": 0.0,
    }
    if model is not None:
        completion_kwargs["model"] = model
    result = client.complete(CompletionRequest(**completion_kwargs))  # type: ignore[arg-type]
    payload = parse_json_response(result.content)
    return DirectionalMemo.model_validate(payload)


__all__ = [
    "DirectionalMemo",
    "Horizon",
    "LabeledMemo",
    "SentimentAggregationRequest",
    "analyze",
]
