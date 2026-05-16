from datetime import UTC, date, datetime

from data.jpx import FuturesBar, FuturesQuote, StubJpxClient, get_client


def test_stub_returns_configured_quote():
    quote = FuturesQuote(
        symbol="NK225M6",
        timestamp=datetime(2026, 5, 11, 8, 30, tzinfo=UTC),
        last=38500.0,
        prev_close=38400.0,
        is_special_quote=True,
    )
    client = StubJpxClient(quote=quote)
    assert client.get_quote("NK225M6") is quote


def test_stub_default_quote_uses_base_price():
    client = StubJpxClient(base_price=39000.0)
    q = client.get_quote("NK225M6")
    assert q.symbol == "NK225M6"
    assert q.last == 39000.0
    assert q.prev_close == 39000.0


def test_stub_get_bars_filters_by_time_window():
    bars = [
        FuturesBar(
            timestamp=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
            open=1, high=1, low=1, close=1, volume=10,
        ),
        FuturesBar(
            timestamp=datetime(2026, 5, 11, 1, 0, tzinfo=UTC),
            open=2, high=2, low=2, close=2, volume=20,
        ),
        FuturesBar(
            timestamp=datetime(2026, 5, 11, 2, 0, tzinfo=UTC),
            open=3, high=3, low=3, close=3, volume=30,
        ),
    ]
    client = StubJpxClient(bars={"NK225M6": bars})
    got = client.get_bars(
        "NK225M6",
        interval="1h",
        start=datetime(2026, 5, 11, 0, 30, tzinfo=UTC),
        end=datetime(2026, 5, 11, 1, 30, tzinfo=UTC),
    )
    assert [b.volume for b in got] == [20]


def test_stub_open_interest_lookup_and_default():
    client = StubJpxClient(open_interest={("NK225M6", date(2026, 5, 11)): 123_456})
    assert client.get_open_interest("NK225M6", on=date(2026, 5, 11)) == 123_456
    assert client.get_open_interest("NK225M6", on=date(2026, 5, 12)) == 0


def test_get_client_returns_stub():
    assert isinstance(get_client(), StubJpxClient)
