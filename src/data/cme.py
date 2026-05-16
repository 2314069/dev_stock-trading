"""CME 日経先物データ取得 IF。

SPEC §F-08 (c) クロスマーケット特徴量で利用される、CME 日経（円建 / ドル建）の OSE 休止中
リターン、出来高・建玉、OSE-CME オーバーラップ時の乖離などを提供する。Stage 0 ではスタブのみで、
Stage 1+ で CME DataMine / ベンダ実装へ差替える。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel

Denomination = Literal["JPY", "USD"]


class CmeNikkeiBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    denomination: Denomination


class CmeNikkeiQuote(BaseModel):
    """CME 日経スナップショット。OSE 休止中の参照値として使う。"""

    denomination: Denomination
    timestamp: datetime
    last: float
    prev_settle: float
    session_open: float | None = None
    session_high: float | None = None
    session_low: float | None = None


class CmeClient(Protocol):
    def get_quote(self, denomination: Denomination) -> CmeNikkeiQuote: ...

    def get_bars(
        self,
        denomination: Denomination,
        *,
        start: datetime,
        end: datetime,
    ) -> list[CmeNikkeiBar]: ...


class StubCmeClient:
    def __init__(
        self,
        quotes: dict[Denomination, CmeNikkeiQuote] | None = None,
        bars: dict[Denomination, list[CmeNikkeiBar]] | None = None,
        *,
        base_price: float = 38000.0,
    ) -> None:
        self._quotes = quotes or {}
        self._bars = bars or {}
        self._base_price = base_price

    def get_quote(self, denomination: Denomination) -> CmeNikkeiQuote:
        if denomination in self._quotes:
            return self._quotes[denomination]
        return CmeNikkeiQuote(
            denomination=denomination,
            timestamp=datetime.now(),
            last=self._base_price,
            prev_settle=self._base_price,
        )

    def get_bars(
        self,
        denomination: Denomination,
        *,
        start: datetime,
        end: datetime,
    ) -> list[CmeNikkeiBar]:
        return [b for b in self._bars.get(denomination, []) if start <= b.timestamp <= end]


def get_client() -> CmeClient:
    """Stage 0 では常に StubCmeClient。Stage 1+ で CME / ベンダ実装へ差替える。"""
    return StubCmeClient()


__all__ = [
    "CmeClient",
    "CmeNikkeiBar",
    "CmeNikkeiQuote",
    "Denomination",
    "StubCmeClient",
    "get_client",
]
