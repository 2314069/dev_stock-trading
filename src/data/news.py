"""F-09 ニュース取得・正規化レイヤー。

SPEC §F-09 のとおり、ソース別アダプタ → 共通スキーマへの正規化 → 重複排除 → NLP（カテゴリ /
インパクト / センチメント）まで適用したアイテムを提供する。F-08 の News Analyst と F-09 の UI が
共通で消費する契約。Stage 0 ではスタブのみで、Stage 1+ で RSS / API アダプタを実装する。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

Impact = Literal["Low", "Medium", "High"]

_IMPACT_RANK: dict[str, int] = {"Low": 0, "Medium": 1, "High": 2}


class NewsItem(BaseModel):
    """正規化後のニュース 1 件 + NLP 結果。"""

    timestamp: datetime
    source: str
    headline: str
    summary: str | None = None
    categories: list[str] = Field(default_factory=list)
    impact: Impact = "Low"
    sentiment: float = Field(0.0, ge=-1.0, le=1.0)
    url: str | None = None


class NewsQuery(BaseModel):
    """ニュース取得クエリ。指定フィールドはすべて AND 条件。"""

    since: datetime | None = None
    until: datetime | None = None
    sources: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    min_impact: Impact = "Low"
    limit: int = Field(50, ge=1)


class NewsFetcher(Protocol):
    def fetch(self, query: NewsQuery) -> list[NewsItem]: ...


class StubNewsFetcher:
    """Stage 0 / テスト用。コンストラクタに渡したアイテムを query でフィルタして返す。"""

    def __init__(self, items: list[NewsItem] | None = None) -> None:
        self._items = list(items or [])

    def fetch(self, query: NewsQuery) -> list[NewsItem]:
        min_rank = _IMPACT_RANK[query.min_impact]
        sources = set(query.sources)
        categories = set(query.categories)
        out: list[NewsItem] = []
        for item in self._items:
            if query.since is not None and item.timestamp < query.since:
                continue
            if query.until is not None and item.timestamp > query.until:
                continue
            if sources and item.source not in sources:
                continue
            if categories and not (categories & set(item.categories)):
                continue
            if _IMPACT_RANK[item.impact] < min_rank:
                continue
            out.append(item)
        out.sort(key=lambda x: x.timestamp)
        return out[: query.limit]


def get_fetcher() -> NewsFetcher:
    """Stage 0 では常に StubNewsFetcher。Stage 1+ で RSS / API アダプタへ差替える。"""
    return StubNewsFetcher()


__all__ = [
    "Impact",
    "NewsFetcher",
    "NewsItem",
    "NewsQuery",
    "StubNewsFetcher",
    "get_fetcher",
]
