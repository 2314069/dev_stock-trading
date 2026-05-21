"""F-08 エージェント間で共有する型定義。

各エージェント (News / Technical / Sentiment / Researcher Bull-Bear / Portfolio Manager) は
共通の出力スキーマ (`DirectionalMemo`) を返すことで、Portfolio Manager / グラフ層が
エージェント本体を区別せずに集約できるようにする。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

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


class DirectionProbabilities(BaseModel):
    """3 値方向の確率分布。総和が ~1.0 (±0.01) であることを後検証。"""

    bullish: float = Field(ge=0.0, le=1.0)
    neutral: float = Field(ge=0.0, le=1.0)
    bearish: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_sum(self) -> DirectionProbabilities:
        total = self.bullish + self.neutral + self.bearish
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"probabilities must sum to ~1.0, got {total:.4f}")
        return self


class PortfolioPlan(BaseModel):
    """Portfolio Manager が出力する最終シナリオ。

    SPEC §F-08 のうち LLM で生成可能な部分（方向 / 確率分布 / 信頼度 / 寄与要因 / シナリオ /
    bull・bear 各論）を担う。予測レンジ・ポイント予測・類似日は ML モデル側の責務として分離。
    """

    horizon: Horizon
    direction: Literal["bullish", "neutral", "bearish"]
    direction_probabilities: DirectionProbabilities
    confidence: int = Field(ge=0, le=100)
    top_drivers: list[str] = Field(default_factory=list, max_length=5)
    scenario: str
    bull_case: str = ""
    bear_case: str = ""


class ActualOutcome(BaseModel):
    """fixture の答え合わせ用。後日実際の値が判明したら埋める。eval/scorers から参照される。"""

    horizon: Horizon
    actual_direction: Literal["bullish", "neutral", "bearish"]
    actual_open: float | None = None
    actual_close: float | None = None
    open_return: float | None = None
    note: str = ""


__all__ = [
    "ActualOutcome",
    "DirectionProbabilities",
    "DirectionalMemo",
    "Horizon",
    "LabeledMemo",
    "PortfolioPlan",
]
