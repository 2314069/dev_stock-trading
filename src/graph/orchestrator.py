"""F-08 予測パイプラインのオーケストレーション抽象。

このモジュールはオーケストレーションフレームワーク (LangGraph / CrewAI / 自作 など) を
1 つに固定しないための薄い IF を提供する。具体実装は `src/graph/` 配下に並べ、
`get_orchestrator()` でファクトリ差替する。

責務:
- `PredictionRequest` (どのホライゾン・どの時刻・どのシンボル) を受け取り、
  `PortfolioPlan` を返す
- データ取得・各エージェント呼出・議論ラウンド管理は実装側の内部詳細

依存方針:
- 本ファイルは具象オーケストレータ実装に依存しない（実装はファクトリ経由でのみ参照）
- データ層クライアントは具象実装のコンストラクタで注入する（DI）
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from agents.types import (
    DirectionProbabilities,
    Horizon,
    PortfolioPlan,
)


class PredictionRequest(BaseModel):
    """予測リクエスト。"""

    horizon: Horizon
    as_of: datetime
    symbol: str
    # 任意の追加コンテキスト（実装側で参照するかは任意）。将来の拡張用
    extra: dict[str, object] = Field(default_factory=dict)


class Orchestrator(Protocol):
    """F-08 予測パイプラインを 1 回回すための IF。

    実装側はコンストラクタで LLMClient / NewsFetcher / JpxClient / FxClient / CmeClient などを
    受け取り、`predict()` 内部で各エージェントをチェーンする。
    """

    def predict(self, req: PredictionRequest) -> PortfolioPlan: ...


class StubOrchestrator:
    """Stage 0 / テスト用。決定論的に canned な `PortfolioPlan` を返す。

    実 LLM や実データに触らずパイプライン下流（API / 表示層 / 評価層）を組み立てるのに使う。
    """

    def __init__(self, *, plan: PortfolioPlan | None = None) -> None:
        self._plan = plan

    def predict(self, req: PredictionRequest) -> PortfolioPlan:
        if self._plan is not None:
            return self._plan.model_copy(update={"horizon": req.horizon})
        return PortfolioPlan(
            horizon=req.horizon,
            direction="neutral",
            direction_probabilities=DirectionProbabilities(
                bullish=0.33, neutral=0.34, bearish=0.33
            ),
            confidence=10,
            top_drivers=[],
            scenario="(stub: 実装未差替のため判定保留)",
            bull_case="",
            bear_case="",
        )


def get_orchestrator() -> Orchestrator:
    """Stage 0 では常に StubOrchestrator。実装が揃ったら LangGraph 実装などへ差替える。"""
    return StubOrchestrator()


__all__ = [
    "Orchestrator",
    "PredictionRequest",
    "StubOrchestrator",
    "get_orchestrator",
]
