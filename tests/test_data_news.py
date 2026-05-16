from datetime import UTC, datetime

from data.news import NewsItem, NewsQuery, StubNewsFetcher, get_fetcher


def _item(
    ts: datetime,
    *,
    source: str = "Reuters",
    headline: str = "x",
    impact: str = "Low",
    categories: list[str] | None = None,
) -> NewsItem:
    return NewsItem(
        timestamp=ts,
        source=source,
        headline=headline,
        impact=impact,  # type: ignore[arg-type]
        categories=categories or [],
    )


def test_stub_returns_items_sorted_by_timestamp():
    a = _item(datetime(2026, 5, 11, 9, 0, tzinfo=UTC), headline="a")
    b = _item(datetime(2026, 5, 11, 8, 0, tzinfo=UTC), headline="b")
    fetcher = StubNewsFetcher([a, b])
    result = fetcher.fetch(NewsQuery())
    assert [it.headline for it in result] == ["b", "a"]


def test_stub_filters_by_time_window():
    items = [
        _item(datetime(2026, 5, 11, 7, 0, tzinfo=UTC), headline="early"),
        _item(datetime(2026, 5, 11, 9, 0, tzinfo=UTC), headline="mid"),
        _item(datetime(2026, 5, 11, 11, 0, tzinfo=UTC), headline="late"),
    ]
    result = StubNewsFetcher(items).fetch(
        NewsQuery(
            since=datetime(2026, 5, 11, 8, 0, tzinfo=UTC),
            until=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        )
    )
    assert [it.headline for it in result] == ["mid"]


def test_stub_filters_by_sources_and_categories():
    items = [
        _item(datetime(2026, 5, 11, 9, 0, tzinfo=UTC), source="Reuters", categories=["macro"]),
        _item(datetime(2026, 5, 11, 9, 1, tzinfo=UTC), source="Bloomberg", categories=["fx"]),
        _item(datetime(2026, 5, 11, 9, 2, tzinfo=UTC), source="Reuters", categories=["fx"]),
    ]
    fetcher = StubNewsFetcher(items)
    by_source = fetcher.fetch(NewsQuery(sources=["Bloomberg"]))
    assert [it.source for it in by_source] == ["Bloomberg"]
    by_cat = fetcher.fetch(NewsQuery(categories=["fx"]))
    assert {it.source for it in by_cat} == {"Bloomberg", "Reuters"}


def test_stub_filters_by_min_impact_and_respects_limit():
    items = [
        _item(datetime(2026, 5, 11, 9, 0, tzinfo=UTC), impact="Low"),
        _item(datetime(2026, 5, 11, 9, 1, tzinfo=UTC), impact="Medium"),
        _item(datetime(2026, 5, 11, 9, 2, tzinfo=UTC), impact="High"),
        _item(datetime(2026, 5, 11, 9, 3, tzinfo=UTC), impact="High"),
    ]
    fetcher = StubNewsFetcher(items)
    high_only = fetcher.fetch(NewsQuery(min_impact="High"))
    assert len(high_only) == 2
    medium_plus = fetcher.fetch(NewsQuery(min_impact="Medium", limit=2))
    assert len(medium_plus) == 2
    assert [it.impact for it in medium_plus] == ["Medium", "High"]


def test_get_fetcher_returns_stub():
    assert isinstance(get_fetcher(), StubNewsFetcher)
