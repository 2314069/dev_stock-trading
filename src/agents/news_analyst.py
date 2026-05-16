"""News Analyst エージェント (F-08 最小構成)。

F-09 が出力するニュース + センチメント特徴量を入力に、指定ホライゾンに向けた方向性メモを返す。
F-08 の他エージェント (Technical / Sentiment / Researcher Bull-Bear / Portfolio Manager) と
並列に動作する想定で、出力 (DirectionalMemo) はオーケストレータが集約する。

設計上の注意:
- SPEC §F-08 のとおり「シナリオ提示」に限定し、売買推奨は出さない。
- ハルシネーション抑制のため、入力ニュースに無い数値・固有名詞を出さないようプロンプトで指示。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from llm.client import (
    CompletionRequest,
    LLMClient,
    Message,
    get_client,
    parse_json_response,
)

Horizon = Literal[
    "open_today",
    "close_today",
    "afternoon_open",
    "night_open",
    "night_close",
    "next_open",
]

Impact = Literal["Low", "Medium", "High"]


class NewsItem(BaseModel):
    """F-09 から渡されるニュース 1 件 + 分類・センチメント結果。"""

    timestamp: datetime
    source: str
    headline: str
    summary: str | None = None
    categories: list[str] = Field(default_factory=list)
    impact: Impact = "Low"
    sentiment: float = Field(0.0, ge=-1.0, le=1.0)
    url: str | None = None


class NewsAnalysisRequest(BaseModel):
    horizon: Horizon
    as_of: datetime
    news: list[NewsItem]


class DirectionalMemo(BaseModel):
    """News Analyst の出力。F-08 のアンサンブル入力 / 寄与要因表示で消費される。"""

    direction: Literal["bullish", "neutral", "bearish"]
    confidence: int = Field(ge=0, le=100)
    key_drivers: list[str] = Field(default_factory=list)
    summary: str


SYSTEM_PROMPT = """\
あなたは日経平均先物のセンチメント分析を担当するアナリストです。
与えられたニュース集合とセンチメントスコアを参照し、指定ホライゾンに向けた方向性メモを返します。

制約:
- 売買推奨は出力しない（統計的シナリオ提示に限定）。
- 元のニュースに記載のない数値・固有名詞・銘柄名を創作しない。
- 高インパクト・公式ソース（中央銀行、取引所開示、経済指標、要人発言）を優先。
- センチメントスコア集計と自分の判定が乖離する場合は乖離理由を summary に簡潔に書く。
- ニュースが乏しい・矛盾する場合は neutral + 低 confidence を返す。

出力は厳密な JSON のみ。前後に説明文・フェンスを付けない。スキーマ:
{
  "direction": "bullish" | "neutral" | "bearish",
  "confidence": 0-100 の整数,
  "key_drivers": ["寄与した記事の見出し", ...] (最大 5 件、入力に存在する見出しから選ぶ),
  "summary": "100 字程度の方向性メモ"
}
"""


def _format_news(news: list[NewsItem]) -> str:
    if not news:
        return "(ニュース無し)"
    lines: list[str] = []
    for n in sorted(news, key=lambda x: x.timestamp):
        cat = "/".join(n.categories) if n.categories else "-"
        body = n.summary or n.headline
        lines.append(
            f"- [{n.timestamp.isoformat()}] [{n.source}] [{cat}] "
            f"[impact={n.impact}] [sent={n.sentiment:+.2f}] "
            f"見出し: {n.headline}"
            + (f" / 要約: {body}" if n.summary else "")
        )
    return "\n".join(lines)


def _build_user_message(req: NewsAnalysisRequest) -> str:
    return (
        f"対象ホライゾン: {req.horizon}\n"
        f"基準時刻 (as_of): {req.as_of.isoformat()}\n"
        f"ニュース件数: {len(req.news)}\n\n"
        f"ニュース一覧:\n{_format_news(req.news)}\n\n"
        "上記から方向性メモを上記スキーマの JSON のみで返してください。"
    )


def analyze(
    req: NewsAnalysisRequest,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
) -> DirectionalMemo:
    """News Analyst を 1 回実行する。"""
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
    "Impact",
    "NewsAnalysisRequest",
    "NewsItem",
    "analyze",
]
