"""為替データ取得 IF。

SPEC §F-08 (e) クロスアセットで利用される USD/JPY などのレベル・前日比・ボラ・リスクリバーサル
（OTM プット IV − OTM コール IV）を提供する。Stage 0 ではスタブのみ。
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class FxQuote(BaseModel):
    pair: str
    timestamp: datetime
    last: float
    prev_close: float

    @property
    def change(self) -> float:
        return self.last - self.prev_close

    @property
    def change_pct(self) -> float:
        if not self.prev_close:
            return 0.0
        return self.last / self.prev_close - 1.0


class RiskReversal(BaseModel):
    """OTM プット IV − OTM コール IV。単位はボラポイント。25-delta / 1M が一般的。"""

    pair: str
    timestamp: datetime
    tenor: str
    delta: float = 0.25
    value: float


class FxClient(Protocol):
    def get_quote(self, pair: str) -> FxQuote: ...

    def get_risk_reversal(
        self,
        pair: str,
        *,
        tenor: str = "1M",
        delta: float = 0.25,
    ) -> RiskReversal: ...


class StubFxClient:
    def __init__(
        self,
        quotes: dict[str, FxQuote] | None = None,
        risk_reversals: dict[tuple[str, str, float], RiskReversal] | None = None,
        *,
        default_level: float = 150.0,
    ) -> None:
        self._quotes = quotes or {}
        self._rr = risk_reversals or {}
        self._default_level = default_level

    def get_quote(self, pair: str) -> FxQuote:
        if pair in self._quotes:
            return self._quotes[pair]
        return FxQuote(
            pair=pair,
            timestamp=datetime.now(),
            last=self._default_level,
            prev_close=self._default_level,
        )

    def get_risk_reversal(
        self,
        pair: str,
        *,
        tenor: str = "1M",
        delta: float = 0.25,
    ) -> RiskReversal:
        key = (pair, tenor, delta)
        if key in self._rr:
            return self._rr[key]
        return RiskReversal(
            pair=pair,
            timestamp=datetime.now(),
            tenor=tenor,
            delta=delta,
            value=0.0,
        )


def get_client() -> FxClient:
    """Stage 0 では常に StubFxClient。Stage 1+ で実 FX フィードへ差替える。"""
    return StubFxClient()


__all__ = [
    "FxClient",
    "FxQuote",
    "RiskReversal",
    "StubFxClient",
    "get_client",
]
