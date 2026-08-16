import pytest

from scripts.economics import EconomicsInput, calculate


def test_economics_is_reproducible() -> None:
    result = calculate(
        EconomicsInput(
            events_per_day=100,
            seconds_saved_per_event=10,
            working_days_per_year=250,
            hourly_cost=1000,
            adoption=0.5,
            capex=100_000,
            annual_opex=10_000,
        )
    )
    assert result.annual_hours_saved == pytest.approx(34.7222222)
    assert result.annual_gross_value == pytest.approx(34_722.2222)
    assert result.annual_net_value == pytest.approx(24_722.2222)
    assert result.payback_years == pytest.approx(4.0449438)


def test_invalid_adoption_is_rejected() -> None:
    with pytest.raises(ValueError):
        calculate(EconomicsInput(1, 1, 1, 1, 1.1, 0, 0))
