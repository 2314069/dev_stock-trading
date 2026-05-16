from datetime import UTC, datetime

import pytest

from data.fx import FxQuote, RiskReversal, StubFxClient, get_client


def test_fx_quote_change_and_change_pct():
    q = FxQuote(
        pair="USDJPY",
        timestamp=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
        last=151.5,
        prev_close=150.0,
    )
    assert q.change == pytest.approx(1.5)
    assert q.change_pct == pytest.approx(0.01)


def test_fx_quote_change_pct_handles_zero_prev_close():
    q = FxQuote(
        pair="USDJPY",
        timestamp=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
        last=151.5,
        prev_close=0.0,
    )
    assert q.change_pct == 0.0


def test_stub_returns_configured_quote_else_default():
    configured = FxQuote(
        pair="USDJPY",
        timestamp=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
        last=151.0,
        prev_close=150.0,
    )
    client = StubFxClient(quotes={"USDJPY": configured}, default_level=160.0)
    assert client.get_quote("USDJPY") is configured
    fallback = client.get_quote("EURJPY")
    assert fallback.pair == "EURJPY"
    assert fallback.last == 160.0


def test_stub_risk_reversal_lookup_and_default():
    configured = RiskReversal(
        pair="USDJPY",
        timestamp=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
        tenor="1M",
        delta=0.25,
        value=-1.2,
    )
    client = StubFxClient(risk_reversals={("USDJPY", "1M", 0.25): configured})
    assert client.get_risk_reversal("USDJPY") is configured
    default = client.get_risk_reversal("USDJPY", tenor="3M")
    assert default.tenor == "3M"
    assert default.value == 0.0


def test_get_client_returns_stub():
    assert isinstance(get_client(), StubFxClient)
