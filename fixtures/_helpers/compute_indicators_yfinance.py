"""fixtures/<id>/technicals.json 構築スクリプト。

yfinance から直近 250 営業日の OHLCV を取得し、
src/agents/technical_analyst.py の TechnicalIndicators スキーマに沿った JSON を出力する。

architectures/a01_f08_subagent/playbook.md の Step 1B (fresh モード) で使う。
network allowlist に yahoo finance が含まれる環境でのみ動作。

使い方:
  uv run python fixtures/_helpers/compute_indicators_yfinance.py \\
    --symbol ^N225 --as-of 2026-05-18T15:15:00+09:00 --horizon next_open \\
    --out fixtures/2026-05-19_macro_heavy/technicals.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import yfinance as yf
import pandas as pd


def wilder_rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    # Wilder's smoothing = EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return None if math.isnan(val) else float(val)


def macd(close: pd.Series) -> tuple[float | None, float | None]:
    if len(close) < 26:
        return None, None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal.iloc[-1])


def bollinger_width(close: pd.Series, period: int = 25, k: float = 2.0) -> float | None:
    if len(close) < period:
        return None
    rolling = close.rolling(period)
    mid = rolling.mean()
    std = rolling.std(ddof=0)
    upper = mid + k * std
    lower = mid - k * std
    width = (upper - lower) / mid
    val = width.iloc[-1]
    return None if math.isnan(val) else float(val)


def atr_14(high: pd.Series, low: pd.Series, close: pd.Series) -> float | None:
    if len(close) < 15:
        return None
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    val = atr.iloc[-1]
    return None if math.isnan(val) else float(val)


def ichimoku_position(high: pd.Series, low: pd.Series, close: pd.Series) -> str | None:
    """先行スパン A/B と現在価格の位置関係。"""
    if len(close) < 52:
        return None
    conv = (high.rolling(9).max() + low.rolling(9).min()) / 2
    base = (high.rolling(26).max() + low.rolling(26).min()) / 2
    # 先行スパン A は (conv + base) / 2 を 26 日先行表示。
    # 現在の雲は 26 日前の値で構成される。
    span_a_now = ((conv + base) / 2).shift(26)
    span_b_now = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    a = span_a_now.iloc[-1]
    b = span_b_now.iloc[-1]
    if math.isnan(a) or math.isnan(b):
        return None
    upper = max(a, b)
    lower = min(a, b)
    c = float(close.iloc[-1])
    if c > upper:
        return "above"
    if c < lower:
        return "below"
    return "inside"


def safe_float(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="^N225")
    ap.add_argument("--as-of", required=True, help="ISO8601, e.g. 2026-05-18T15:15:00+09:00")
    ap.add_argument("--horizon", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    SYMBOL = args.symbol
    AS_OF = datetime.fromisoformat(args.as_of)

    print(f"Fetching {SYMBOL} ...", file=sys.stderr)
    df = yf.download(
        SYMBOL,
        period="2y",
        interval="1d",
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        print(f"No data for {SYMBOL}", file=sys.stderr)
        return 1
    # yfinance can return MultiIndex columns for single ticker downloads
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=["Close"])
    print(f"Got {len(df)} rows, latest: {df.index[-1]}", file=sys.stderr)

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    open_ = df["Open"].astype(float)
    volume = df["Volume"].astype(float)

    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    sma_5 = safe_float(close.rolling(5).mean().iloc[-1])
    sma_25 = safe_float(close.rolling(25).mean().iloc[-1])
    sma_75 = safe_float(close.rolling(75).mean().iloc[-1])
    sma_200 = safe_float(close.rolling(200).mean().iloc[-1])
    rsi = wilder_rsi(close)
    m, ms = macd(close)
    bw = bollinger_width(close)
    atr = atr_14(high, low, close)
    cloud = ichimoku_position(high, low, close)

    indicators = {
        "last_price": last,
        "prev_close": prev,
        "sma_5": sma_5,
        "sma_25": sma_25,
        "sma_75": sma_75,
        "sma_200": sma_200,
        "rsi_14": rsi,
        "macd": m,
        "macd_signal": ms,
        "bollinger_width": bw,
        "atr_14": atr,
        "ichimoku_cloud_position": cloud,
        "overnight_return": None,  # ^N225 は現物指数のため夜間値なし
    }

    # recent_bars: 直近 10 本
    tz = AS_OF.tzinfo
    bars = []
    for ts, row in df.tail(10).iterrows():
        # ^N225 は終日 1 セッション。session 区分は "day" 固定。
        bars.append(
            {
                "symbol": SYMBOL,
                "timestamp": ts.to_pydatetime().replace(tzinfo=tz).isoformat(),
                "session": "day",
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if not math.isnan(row["Volume"]) else 0,
            }
        )

    out = {
        "symbol": SYMBOL,
        "as_of": AS_OF.isoformat(),
        "horizon": args.horizon,
        "data_latest_date": df.index[-1].date().isoformat(),
        "indicators": indicators,
        "recent_bars": bars,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"Wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
