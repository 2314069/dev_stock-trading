"""JPX / OSE 日経225先物データ取得 IF。

SPEC §F-08 (a)(b)(d)(g) で利用される、日中・ナイト両セッションの OHLCV、期近 / 期先の出来高シェア、
建玉、寄付前気配などを提供する。Stage 0 ではスタブのみで、Stage 1+ で実 API / ベンダフィードへ
差替える。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Protocol

from pydantic import BaseModel

Session = Literal["day", "night"]
BarInterval = Literal["1m", "5m", "15m", "30m", "1h", "1d"]


class FuturesBar(BaseModel):
    """先物 1 本足。"""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: int | None = None
    session: Session = "day"


class FuturesQuote(BaseModel):
    """期近スナップショット。寄付前気配・特別気配の表示にも使う。"""

    symbol: str
    timestamp: datetime
    last: float
    prev_close: float
    bid: float | None = None
    ask: float | None = None
    bid_size: int | None = None
    ask_size: int | None = None
    is_special_quote: bool = False


class JpxClient(Protocol):
    def get_quote(self, symbol: str) -> FuturesQuote: ...

    def get_bars(
        self,
        symbol: str,
        *,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> list[FuturesBar]: ...

    def get_open_interest(self, symbol: str, *, on: date) -> int: ...


class StubJpxClient:
    """Stage 0 用。乱数を使わず、コンストラクタで渡したデータを決定論的に返す。"""

    def __init__(
        self,
        *,
        base_price: float = 38000.0,
        quote: FuturesQuote | None = None,
        bars: dict[str, list[FuturesBar]] | None = None,
        open_interest: dict[tuple[str, date], int] | None = None,
    ) -> None:
        self._base_price = base_price
        self._quote = quote
        self._bars = bars or {}
        self._open_interest = open_interest or {}

    def get_quote(self, symbol: str) -> FuturesQuote:
        if self._quote is not None:
            return self._quote
        return FuturesQuote(
            symbol=symbol,
            timestamp=datetime.now(),
            last=self._base_price,
            prev_close=self._base_price,
        )

    def get_bars(
        self,
        symbol: str,
        *,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> list[FuturesBar]:
        return [b for b in self._bars.get(symbol, []) if start <= b.timestamp <= end]

    def get_open_interest(self, symbol: str, *, on: date) -> int:
        return self._open_interest.get((symbol, on), 0)


def get_client() -> JpxClient:
    """Stage 0 では常に StubJpxClient。Stage 1+ で JPX 公式 / ベンダ実装へ差替える。"""
    return StubJpxClient()


__all__ = [
    "BarInterval",
    "FuturesBar",
    "FuturesQuote",
    "JpxClient",
    "Session",
    "StubJpxClient",
    "get_client",
]
