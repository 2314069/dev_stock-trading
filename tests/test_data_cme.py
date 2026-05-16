from datetime import UTC, datetime

from data.cme import CmeNikkeiBar, CmeNikkeiQuote, StubCmeClient, get_client


def test_stub_returns_configured_quote():
    q = CmeNikkeiQuote(
        denomination="JPY",
        timestamp=datetime(2026, 5, 11, 6, 0, tzinfo=UTC),
        last=38600.0,
        prev_settle=38500.0,
    )
    client = StubCmeClient(quotes={"JPY": q})
    assert client.get_quote("JPY") is q


def test_stub_default_quote_per_denomination():
    client = StubCmeClient(base_price=39000.0)
    jpy = client.get_quote("JPY")
    usd = client.get_quote("USD")
    assert jpy.denomination == "JPY"
    assert usd.denomination == "USD"
    assert jpy.last == usd.last == 39000.0


def test_stub_get_bars_filters_by_time_window():
    bars = [
        CmeNikkeiBar(
            timestamp=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
            open=1, high=1, low=1, close=1, volume=10, denomination="JPY",
        ),
        CmeNikkeiBar(
            timestamp=datetime(2026, 5, 11, 1, 0, tzinfo=UTC),
            open=2, high=2, low=2, close=2, volume=20, denomination="JPY",
        ),
    ]
    client = StubCmeClient(bars={"JPY": bars})
    got = client.get_bars(
        "JPY",
        start=datetime(2026, 5, 11, 0, 30, tzinfo=UTC),
        end=datetime(2026, 5, 11, 2, 0, tzinfo=UTC),
    )
    assert [b.volume for b in got] == [20]


def test_get_client_returns_stub():
    assert isinstance(get_client(), StubCmeClient)
