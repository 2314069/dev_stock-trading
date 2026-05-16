from datetime import UTC, datetime

from agents.types import DirectionProbabilities, PortfolioPlan
from graph.orchestrator import (
    PredictionRequest,
    StubOrchestrator,
    get_orchestrator,
)


def _request(horizon: str = "open_today") -> PredictionRequest:
    return PredictionRequest(
        horizon=horizon,  # type: ignore[arg-type]
        as_of=datetime(2026, 5, 11, 7, 30, tzinfo=UTC),
        symbol="NK225M6",
    )


def test_get_orchestrator_returns_stub_by_default():
    assert isinstance(get_orchestrator(), StubOrchestrator)


def test_stub_default_plan_is_neutral_low_confidence():
    plan = StubOrchestrator().predict(_request())
    assert isinstance(plan, PortfolioPlan)
    assert plan.direction == "neutral"
    assert plan.confidence == 10
    assert plan.horizon == "open_today"


def test_stub_returns_configured_plan_with_horizon_overridden():
    canned = PortfolioPlan(
        horizon="close_today",
        direction="bullish",
        direction_probabilities=DirectionProbabilities(
            bullish=0.6, neutral=0.3, bearish=0.1
        ),
        confidence=70,
        top_drivers=["FOMC ハト派傾斜"],
        scenario="canned",
    )
    orch = StubOrchestrator(plan=canned)
    # 別ホライゾンで呼び出すと、horizon は req 由来で上書きされる
    plan = orch.predict(_request(horizon="night_open"))
    assert plan.horizon == "night_open"
    assert plan.direction == "bullish"
    assert plan.confidence == 70
