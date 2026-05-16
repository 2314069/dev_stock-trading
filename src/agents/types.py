"""F-08 エージェント間で共有する型定義。

各エージェント (News / Technical / Sentiment / Researcher Bull-Bear / Portfolio Manager) は
共通の出力スキーマ (`DirectionalMemo`) を返すことで、Portfolio Manager / グラフ層が
エージェント本体を区別せずに集約できるようにする。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Horizon = Literal[
    "open_today",
    "close_today",
    "afternoon_open",
    "night_open",
    "night_close",
    "next_open",
]


class DirectionalMemo(BaseModel):
    """F-08 各エージェントが返す共通の方向性メモ。

    `key_drivers` は agent ごとに意味が異なる:
    - News Analyst: 寄与した記事の見出し
    - Technical Analyst: シグナルを出した指標の説明 (例: "RSI 28 oversold")
    - Researcher Bull/Bear: 根拠となった観点
    どの agent も「売買推奨ではなく統計的シナリオ提示」に留める。
    """

    direction: Literal["bullish", "neutral", "bearish"]
    confidence: int = Field(ge=0, le=100)
    key_drivers: list[str] = Field(default_factory=list)
    summary: str


class LabeledMemo(BaseModel):
    """ラベル付きメモ。`label` は出所文脈 (例: "central_bank", "domestic_news", "technical")。

    Sentiment Aggregator / Researcher Bull-Bear など、複数の `DirectionalMemo` を入力に取る
    エージェントが共通で使う。
    """

    label: str
    memo: DirectionalMemo


__all__ = ["DirectionalMemo", "Horizon", "LabeledMemo"]
