"""Technical Analyst エージェント (F-08)。

SPEC §F-08 (a)(b)(k) のテクニカル指標スナップショットを入力に、指定ホライゾンに向けた
方向性メモを返す。指標値の計算自体は `src/features/` の責務とし、本エージェントは
「指標 → 方向性判断」変換のみに集中する。

News Analyst と同じ `DirectionalMemo` を返すことで、Portfolio Manager / グラフ層は
エージェント本体を区別せずに集約できる。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from agents.types import DirectionalMemo, Horizon
from data.jpx import FuturesBar
from llm.client import (
    CompletionRequest,
    LLMClient,
    Message,
    get_client,
    parse_json_response,
)

CloudPosition = Literal["above", "inside", "below"]


class TechnicalIndicators(BaseModel):
    """SPEC §F-08 (a)(b)(k) の主要テクニカル指標スナップショット。

    値が取得不能な指標は None のまま渡す（プロンプトでも欠損として明示される）。
    """

    last_price: float
    prev_close: float
    sma_5: float | None = None
    sma_25: float | None = None
    sma_75: float | None = None
    sma_200: float | None = None
    rsi_14: float | None = Field(default=None, ge=0.0, le=100.0)
    macd: float | None = None
    macd_signal: float | None = None
    bollinger_width: float | None = Field(default=None, ge=0.0)
    atr_14: float | None = Field(default=None, ge=0.0)
    ichimoku_cloud_position: CloudPosition | None = None
    overnight_return: float | None = None  # ナイト終値 − 前日大引け


class TechnicalAnalysisRequest(BaseModel):
    horizon: Horizon
    as_of: datetime
    symbol: str
    indicators: TechnicalIndicators
    recent_bars: list[FuturesBar] = Field(default_factory=list)


SYSTEM_PROMPT = """\
あなたは日経平均先物のテクニカル分析を担当するアナリストです。
与えられた指標スナップショットと（あれば）直近の足を参照し、指定ホライゾンに向けた方向性メモを返します。

制約:
- 売買推奨は出力しない（統計的シナリオ提示に限定）。
- 入力に無い指標値・水準・固有名詞を創作しない。欠損 (None) の指標は判断材料に使わない。
- シグナルが互いに矛盾する場合（例: RSI 過熱だが MACD 強気クロス）は乖離理由を summary に書く。
- 指標が乏しい・矛盾する場合は neutral + 低 confidence を返す。
- ホライゾンが寄付前 (open_today / afternoon_open / night_open / next_open) の場合はオーバーナイト系
  指標を、引け予測 (close_today / night_close) の場合は日中モメンタム系指標を相対的に重視する。

出力は厳密な JSON のみ。前後に説明文・フェンスを付けない。スキーマ:
{
  "direction": "bullish" | "neutral" | "bearish",
  "confidence": 0-100 の整数,
  "key_drivers": ["シグナルを出した指標の説明", ...] (最大 5 件、入力に存在する指標から選ぶ),
  "summary": "100 字程度の方向性メモ"
}
"""


def _fmt(value: float | None, *, fmt: str = ".4f") -> str:
    return "None" if value is None else format(value, fmt)


def _format_indicators(ind: TechnicalIndicators) -> str:
    change_pct = (ind.last_price / ind.prev_close - 1.0) if ind.prev_close else 0.0
    return "\n".join(
        [
            f"- last={ind.last_price:.2f}, prev_close={ind.prev_close:.2f} "
            f"(change={change_pct:+.4%})",
            f"- SMA: 5={_fmt(ind.sma_5, fmt='.2f')}, 25={_fmt(ind.sma_25, fmt='.2f')}, "
            f"75={_fmt(ind.sma_75, fmt='.2f')}, 200={_fmt(ind.sma_200, fmt='.2f')}",
            f"- RSI(14)={_fmt(ind.rsi_14, fmt='.2f')}",
            f"- MACD={_fmt(ind.macd, fmt='.4f')}, signal={_fmt(ind.macd_signal, fmt='.4f')}",
            f"- Bollinger width={_fmt(ind.bollinger_width, fmt='.4f')}, "
            f"ATR(14)={_fmt(ind.atr_14, fmt='.4f')}",
            f"- 一目均衡表 雲との位置={ind.ichimoku_cloud_position or 'None'}",
            f"- オーバーナイトリターン={_fmt(ind.overnight_return, fmt='+.4%')}",
        ]
    )


def _format_bars(bars: list[FuturesBar]) -> str:
    if not bars:
        return "(直近足の提供なし)"
    lines: list[str] = []
    for b in sorted(bars, key=lambda x: x.timestamp):
        lines.append(
            f"- [{b.timestamp.isoformat()}] [{b.session}] "
            f"O={b.open:.2f} H={b.high:.2f} L={b.low:.2f} C={b.close:.2f} V={b.volume}"
        )
    return "\n".join(lines)


def _build_user_message(req: TechnicalAnalysisRequest) -> str:
    return (
        f"対象シンボル: {req.symbol}\n"
        f"対象ホライゾン: {req.horizon}\n"
        f"基準時刻 (as_of): {req.as_of.isoformat()}\n\n"
        f"指標スナップショット:\n{_format_indicators(req.indicators)}\n\n"
        f"直近足 ({len(req.recent_bars)} 本):\n{_format_bars(req.recent_bars)}\n\n"
        "上記から方向性メモを上記スキーマの JSON のみで返してください。"
    )


def analyze(
    req: TechnicalAnalysisRequest,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
) -> DirectionalMemo:
    """Technical Analyst を 1 回実行する。"""
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
    "CloudPosition",
    "DirectionalMemo",
    "Horizon",
    "TechnicalAnalysisRequest",
    "TechnicalIndicators",
    "analyze",
]
