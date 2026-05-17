"""Portfolio Manager エージェント (F-08 最終ノード)。

News / Technical / Sentiment Aggregator / Researcher Bull・Bear の出力を受け、
SPEC §F-08 で定義された最終シナリオ (`PortfolioPlan`) を生成する。担当範囲は
LLM で生成可能な部分（方向 / 確率分布 / 信頼度 / 寄与要因 / シナリオ要約 / bull・bear 各論）に
限定し、予測レンジ・ポイント予測・類似日は ML モデル側の責務として分離する。

オーケストレーション（議論ターンの繰り返し、複数 Analyst の並列実行など）は `src/graph/`
の責務として後回し。本エージェント自体は純粋なシングルショット LLM 呼び出し。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from agents.types import (
    DirectionalMemo,
    Horizon,
    LabeledMemo,
    PortfolioPlan,
)
from llm.client import LLMClient
from llm.runner import run_json_agent


class PortfolioRequest(BaseModel):
    horizon: Horizon
    as_of: datetime
    symbol: str
    memos: list[LabeledMemo] = Field(default_factory=list)
    bull_memo: DirectionalMemo | None = None
    bear_memo: DirectionalMemo | None = None


SYSTEM_PROMPT = """\
あなたは日経平均先物の Portfolio Manager です。
News / Technical / Sentiment Aggregator / Researcher Bull・Bear から集まったメモ群を統合し、
指定ホライゾンに向けた最終シナリオを生成します。

制約:
- 売買推奨は出力しない（統計的シナリオ提示に限定）。
- 入力に無い数値・固有名詞・銘柄名を創作しない。
- direction は direction_probabilities の最大確率と整合させる（最大確率が neutral なら
  direction も neutral）。
- direction_probabilities は 3 値の和が 1.0（±0.01）になるよう正規化する。
- top_drivers は入力メモ全体から最大 5 件抽出し、入力に存在する観点のみを採用する。
- bull_case / bear_case はそれぞれの memo がある場合は要旨を 1–2 文に要約。無い場合は空文字。
- 入力メモが極端に少ない・全方向で割れる・全 confidence が低い場合は direction=neutral、
  confidence は低めにし、scenario でその不確実性を明示する。

出力は厳密な JSON のみ。前後に説明文・フェンスを付けない。スキーマ:
{
  "direction": "bullish" | "neutral" | "bearish",
  "direction_probabilities": {
    "bullish": 0.0-1.0, "neutral": 0.0-1.0, "bearish": 0.0-1.0
  },
  "confidence": 0-100 の整数,
  "top_drivers": ["寄与要因", ...] (最大 5 件),
  "scenario": "150 字程度の最終シナリオ",
  "bull_case": "強気側の要旨 (1-2 文)、無ければ空文字",
  "bear_case": "弱気側の要旨 (1-2 文)、無ければ空文字"
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


def _format_side(label: str, memo: DirectionalMemo | None) -> str:
    if memo is None:
        return f"({label}: 入力なし)"
    drivers = ", ".join(memo.key_drivers) if memo.key_drivers else "-"
    return (
        f"{label}: direction={memo.direction} confidence={memo.confidence}\n"
        f"  key_drivers: {drivers}\n"
        f"  summary: {memo.summary}"
    )


def _build_user_message(req: PortfolioRequest) -> str:
    return (
        f"対象シンボル: {req.symbol}\n"
        f"対象ホライゾン: {req.horizon}\n"
        f"基準時刻 (as_of): {req.as_of.isoformat()}\n"
        f"入力メモ件数: {len(req.memos)}\n\n"
        f"メモ一覧:\n{_format_memos(req.memos)}\n\n"
        f"{_format_side('Bull Researcher', req.bull_memo)}\n\n"
        f"{_format_side('Bear Researcher', req.bear_memo)}\n\n"
        "上記から最終シナリオを上記スキーマの JSON のみで返してください。"
    )


def synthesize(
    req: PortfolioRequest,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
) -> PortfolioPlan:
    """Portfolio Manager を 1 回実行し、最終シナリオを返す。

    `horizon` は呼び出し側既知の情報のため LLM には echo させず、req から直接埋める。
    """
    return run_json_agent(
        system=SYSTEM_PROMPT,
        user=_build_user_message(req),
        schema=PortfolioPlan,
        client=client,
        model=model,
        max_tokens=1536,
        post_process=lambda payload: {**payload, "horizon": req.horizon},
    )


__all__ = [
    "Horizon",
    "PortfolioPlan",
    "PortfolioRequest",
    "synthesize",
]
