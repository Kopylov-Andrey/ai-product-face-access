"""Tests for economics calculator.

Verifies reproducibility and correctness of economic calculations.
Tests explicit separation of given parameters, assumptions, and calculated results.
Tests proper distinction between ML decision latency (≤1s technical requirement)
and total face passage time (scenario assumption).
"""

import pytest

from scripts.economics import (
    Assumptions,
    GivenParameters,
    calculate,
)


def test_base_case_4s_face_passage() -> None:
    """Base case: 4s face passage time, no queue benefit."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=0.0,
        )
    )

    # CAPEX: 3 entrances × (150k GPU + 2 × 30k cameras) = 630k
    assert result.capex_rub == 630_000

    # OPEX: (5k + 10k) × 12 = 180k
    assert result.annual_opex_rub == 180_000

    # Passage time: (6-4)s × 19,000 × 250 / 3600 = 2,638.89 h
    assert result.passage_time_savings_hours == pytest.approx(2_638.889, rel=1e-3)
    # At 600 ₽/h: 1,583,333 ₽
    assert result.passage_time_savings_rub == pytest.approx(1_583_333, rel=1e-3)

    # Queue: 0 (no assumption)
    assert result.queue_time_savings_hours == 0
    assert result.queue_time_savings_rub == 0

    # FRR (3%): 19,000 × 0.03 × 10s × 250 / 3600 = 395.83 h
    assert result.frr_time_loss_hours == pytest.approx(395.833, rel=1e-3)
    # At 600 ₽/h: 237,500 ₽
    assert result.frr_time_loss_rub == pytest.approx(237_500, rel=1e-3)

    # Net: 1,583,333 - 237,500 - 180,000 = 1,165,833
    expected_net = 1_583_333 - 237_500 - 180_000
    assert result.annual_net_benefit_rub == pytest.approx(expected_net, rel=1e-3)

    # Payback: 630,000 / 1,165,833 ≈ 0.540 years ≈ 197 days
    assert result.payback_period_years == pytest.approx(0.540, rel=1e-2)


def test_downside_5s_face_passage() -> None:
    """Downside scenario: 5s face passage time."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=5.0,
            queue_time_reduction_seconds=0.0,
        )
    )

    # Passage time: (6-5)s × 19,000 × 250 / 3600 = 1,319.44 h
    assert result.passage_time_savings_hours == pytest.approx(1_319.444, rel=1e-3)
    # At 600 ₽/h: 791,667 ₽
    assert result.passage_time_savings_rub == pytest.approx(791_667, rel=1e-3)

    # Net: 791,667 - 237,500 - 180,000 = 374,167
    expected_net = 791_667 - 237_500 - 180_000
    assert result.annual_net_benefit_rub == pytest.approx(expected_net, rel=1e-3)

    # Payback: 630,000 / 374,167 ≈ 1.68 years
    assert result.payback_period_years == pytest.approx(1.68, rel=1e-2)


def test_upside_3s_face_passage() -> None:
    """Upside scenario: 3s face passage time."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=3.0,
            queue_time_reduction_seconds=0.0,
        )
    )

    # Passage time: (6-3)s × 19,000 × 250 / 3600 = 3,958.33 h
    assert result.passage_time_savings_hours == pytest.approx(3_958.333, rel=1e-3)
    # At 600 ₽/h: 2,375,000 ₽
    assert result.passage_time_savings_rub == pytest.approx(2_375_000, rel=1e-3)

    # Net: 2,375,000 - 237,500 - 180,000 = 1,957,500
    expected_net = 2_375_000 - 237_500 - 180_000
    assert result.annual_net_benefit_rub == pytest.approx(expected_net, rel=1e-3)

    # Payback: 630,000 / 1,957,500 ≈ 0.322 years
    assert result.payback_period_years == pytest.approx(0.322, rel=1e-2)


def test_base_case_with_queue_reduction() -> None:
    """Base case + 30s queue reduction."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=30.0,
        )
    )

    # Queue time: 30s × 8,550 peak × 250 / 3600 = 17,812.5 h
    peak_passages = 19_000 * 0.45
    expected_queue_hours = 30 * peak_passages * 250 / 3600
    assert result.queue_time_savings_hours == pytest.approx(expected_queue_hours, rel=1e-3)
    # At 600 ₽/h: 10,687,500 ₽
    assert result.queue_time_savings_rub == pytest.approx(10_687_500, rel=1e-3)

    # Net should include both passage and queue savings
    expected_net = 1_583_333 + 10_687_500 - 237_500 - 180_000
    assert result.annual_net_benefit_rub == pytest.approx(expected_net, rel=1e-3)


def test_guard_workload_reduction() -> None:
    """Test guard workload reduction when modeled."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=0.0,
            target_manual_cases_per_day=10,
        )
    )

    # Guard: (40-10) × 4 min × 250 / 60 = 500 h
    assert result.guard_workload_savings_hours == pytest.approx(500, rel=1e-3)
    # 30 fewer cases/day × 120 ₽/case × 250 days = 900,000 ₽
    assert result.guard_workload_savings_rub == pytest.approx(900_000, rel=1e-3)


def test_card_replacement_reduction() -> None:
    """Test card replacement reduction when modeled."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=0.0,
            card_replacement_reduction_fraction=0.5,
        )
    )

    # Cards: 300 × 0.5 × 250 = 37,500 ₽
    assert result.card_replacement_savings_rub == pytest.approx(37_500, rel=1e-3)


def test_zero_frr_eliminates_time_loss() -> None:
    """Verify that FRR=0 results in no time loss."""
    result = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            target_frr=0.0,
        )
    )

    assert result.frr_time_loss_hours == 0
    assert result.frr_time_loss_rub == 0


def test_high_frr_reduces_net_benefit() -> None:
    """Verify that higher FRR reduces net benefit."""
    low_frr = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            target_frr=0.01,
        )
    )
    high_frr = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            target_frr=0.10,
        )
    )

    assert high_frr.annual_net_benefit_rub < low_frr.annual_net_benefit_rub
    assert high_frr.frr_time_loss_rub > low_frr.frr_time_loss_rub


def test_employee_cost_is_from_given_parameters() -> None:
    """Verify that employee cost comes from given parameters, not assumptions."""
    given = GivenParameters()
    assert given.employee_cost_per_minute_rub == 10.0  # Given in task

    # Custom given parameters should allow changing it
    custom_given = GivenParameters(employee_cost_per_minute_rub=15.0)
    result = calculate(custom_given)

    # Should use the custom rate
    # Passage: (6-4)s × 19,000 × 250 / 3600 = 2,638.89 h
    # At 900 ₽/h (15 ₽/min × 60): 2,375,000 ₽
    assert result.passage_time_savings_rub == pytest.approx(2_375_000, rel=1e-3)


def test_custom_given_parameters() -> None:
    """Test with custom given parameters."""
    given = GivenParameters(
        employees=1_000,
        passages_per_day=2_000,
        peak_percentage=0.5,
        entrances=1,
        cameras_per_entrance=2,
        current_passage_time_seconds=10.0,
        edge_gpu_cost_per_entrance_rub=100_000,
        camera_cost_rub=20_000,
        employee_cost_per_minute_rub=12.0,
    )

    result = calculate(
        given,
        assumptions=Assumptions(
            target_face_passage_time_seconds=5.0,
            target_frr=0.01,
        ),
    )

    # CAPEX: 1 × (100k + 2 × 20k) = 140k
    assert result.capex_rub == 140_000

    # Passage time: (10-5)s × 2,000 × 250 / 3600 = 694.44 h
    assert result.passage_time_savings_hours == pytest.approx(694.444, rel=1e-3)
    # At 720 ₽/h (12 ₽/min × 60): 500,000 ₽
    assert result.passage_time_savings_rub == pytest.approx(500_000, rel=1e-3)


def test_invalid_peak_percentage_raises() -> None:
    """Verify that invalid peak_percentage is rejected."""
    with pytest.raises(ValueError, match="peak_percentage must be between 0 and 1"):
        GivenParameters(peak_percentage=1.5)


def test_invalid_target_frr_raises() -> None:
    """Verify that invalid target_frr is rejected."""
    with pytest.raises(ValueError, match="target_frr must be between 0 and 1"):
        Assumptions(target_frr=1.5)


def test_invalid_queue_reduction_raises() -> None:
    """Verify that negative queue_time_reduction_seconds is rejected."""
    with pytest.raises(ValueError, match="queue_time_reduction_seconds must be non-negative"):
        Assumptions(queue_time_reduction_seconds=-10.0)


def test_invalid_card_replacement_reduction_raises() -> None:
    """Verify that invalid card_replacement_reduction_fraction is rejected."""
    with pytest.raises(
        ValueError, match="card_replacement_reduction_fraction must be between 0 and 1"
    ):
        Assumptions(card_replacement_reduction_fraction=2.0)


def test_result_string_representation() -> None:
    """Verify that EconomicsResult has useful string representation."""
    result = calculate()
    result_str = str(result)

    # Check key sections present
    assert "Economics Summary" in result_str
    assert "CAPEX" in result_str
    assert "given parameters" in result_str
    assert "Annual OPEX" in result_str
    assert "assumptions" in result_str
    assert "Payback Period" in result_str
    assert "calculated" in result_str
    assert "₽" in result_str


def test_negative_net_benefit_returns_none_payback() -> None:
    """Verify that negative net benefit results in None payback period."""
    # Create parameters with very low usage and high OPEX
    given = GivenParameters(passages_per_day=10)
    assumptions = Assumptions(
        monthly_maintenance_rub=100_000,
        monthly_operations_rub=100_000,
    )

    result = calculate(given, assumptions)

    # Net benefit should be negative
    assert result.annual_net_benefit_rub < 0
    # Payback should be None
    assert result.payback_period_years is None


def test_scenarios_are_distinct() -> None:
    """Verify that different face passage scenarios produce different results."""
    downside = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=5.0,
            queue_time_reduction_seconds=0.0,
        )
    )
    base = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=0.0,
        )
    )
    upside = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=3.0,
            queue_time_reduction_seconds=0.0,
        )
    )

    # Net benefits should be strictly increasing
    assert downside.annual_net_benefit_rub < base.annual_net_benefit_rub
    assert base.annual_net_benefit_rub < upside.annual_net_benefit_rub

    # Payback should be strictly decreasing
    assert downside.payback_period_years > base.payback_period_years
    assert base.payback_period_years > upside.payback_period_years


def test_frr_sensitivity_matches_documentation() -> None:
    """Verify FRR sensitivity matches product.md documentation."""
    test_cases = [
        (0.01, 79_167, 1_324_167),
        (0.03, 237_500, 1_165_833),
        (0.05, 395_833, 1_007_500),
        (0.10, 791_667, 611_667),
    ]

    for frr, expected_frr_loss, expected_net in test_cases:
        result = calculate(
            assumptions=Assumptions(
                target_frr=frr,
                target_face_passage_time_seconds=4.0,
                queue_time_reduction_seconds=0.0,
            )
        )
        assert result.frr_time_loss_rub == pytest.approx(expected_frr_loss, rel=1e-3)
        assert result.annual_net_benefit_rub == pytest.approx(expected_net, rel=1e-3)
