"""Economics calculator for face-recognition access control system.

All inputs are explicitly labeled as:
- given (supplied task parameters)
- assumption (explicit configurable assumptions)
- calculated (derived results)

IMPORTANT: Card passage time (6s) vs ML decision latency (≤1s) are NOT the same.
ML decision latency is a technical requirement.
Total face passage time depends on approach behavior and must be scenario-assumed.

Separates direct passage time savings from queue effects.
Provides multiple scenarios rather than claiming one as base.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GivenParameters:
    """Supplied task parameters (given, not assumptions)."""

    employees: int = 12_000
    passages_per_day: int = 19_000
    peak_percentage: float = 0.45  # 45% of passages are in peak hours
    entrances: int = 3
    cameras_per_entrance: int = 2
    peak_passages_per_min_per_entrance: int = 20
    working_days_per_year: int = 250

    # Current baseline (given)
    current_passage_time_seconds: float = 6.0
    current_peak_queue_time_seconds: float = 90.0  # Observed, not predicted
    manual_cases_per_day: int = 40
    manual_case_duration_minutes: float = 4.0
    manual_case_cost_rub: float = 120.0
    card_replacements_per_year: int = 300
    card_replacement_cost_rub: float = 250.0

    # Cost (given)
    employee_cost_per_minute_rub: float = 10.0  # Given in task

    # CAPEX (given)
    edge_gpu_cost_per_entrance_rub: float = 150_000.0
    camera_cost_rub: float = 30_000.0

    def __post_init__(self) -> None:
        if self.peak_percentage < 0 or self.peak_percentage > 1:
            raise ValueError("peak_percentage must be between 0 and 1")


@dataclass(frozen=True)
class Assumptions:
    """Explicit assumptions that affect calculations."""

    # Target face passage time (assumption scenario, not measured)
    # ML decision latency <=1s is a technical requirement, NOT total passage time
    # Total face passage depends on approach behavior, camera positioning, etc.
    target_face_passage_time_seconds: float = 4.0  # Base scenario
    target_frr: float = 0.03  # 3% for pilot, must be validated

    # OPEX assumptions
    monthly_maintenance_rub: float = 5_000.0  # Assumption
    monthly_operations_rub: float = 10_000.0  # Assumption

    # FRR impact
    frr_retry_delay_seconds: float = 10.0  # Assumption

    # Queue effect scenarios (assumptions, not proven)
    # How many seconds of the 90s queue are eliminated?
    queue_time_reduction_seconds: float = 0.0  # Default: no queue benefit

    # Guard workload scenarios (assumptions, require Hypothesis 2 validation)
    # How many manual cases per day after deployment?
    target_manual_cases_per_day: int | None = None  # None = not modeled

    # Card replacement scenarios
    card_replacement_reduction_fraction: float = 0.0  # Default: not modeled

    # Planning scenario for security incident cost (NOT actual damage estimate)
    false_accept_incident_cost_rub: float = 500_000.0

    def __post_init__(self) -> None:
        if self.target_frr < 0 or self.target_frr > 1:
            raise ValueError("target_frr must be between 0 and 1")
        if self.queue_time_reduction_seconds < 0:
            raise ValueError("queue_time_reduction_seconds must be non-negative")
        if (
            self.card_replacement_reduction_fraction < 0
            or self.card_replacement_reduction_fraction > 1
        ):
            raise ValueError(
                "card_replacement_reduction_fraction must be between 0 and 1"
            )


@dataclass(frozen=True)
class EconomicsResult:
    """Economic calculation results with explicit labeling."""

    # CAPEX (calculated from given parameters)
    capex_rub: float

    # Annual OPEX (calculated from assumptions)
    annual_opex_rub: float

    # Direct passage time savings (calculated)
    passage_time_savings_hours: float
    passage_time_savings_rub: float

    # Queue time savings (calculated from assumption scenario)
    queue_time_savings_hours: float
    queue_time_savings_rub: float

    # Guard workload savings (calculated from assumption scenario)
    guard_workload_savings_hours: float
    guard_workload_savings_rub: float

    # Card replacement savings (calculated from assumption scenario)
    card_replacement_savings_rub: float

    # FRR impact (calculated cost from assumption)
    frr_time_loss_hours: float
    frr_time_loss_rub: float

    # Totals (calculated)
    annual_gross_benefit_rub: float
    annual_net_benefit_rub: float
    payback_period_years: float | None

    def __str__(self) -> str:
        if self.queue_time_savings_hours == 0:
            queue_note = ""
        else:
            queue_note = (
                f"\n  Queue time savings: {self.queue_time_savings_hours:,.0f} h"
                f"\n    → {self.queue_time_savings_rub:,.0f} ₽ (assumption scenario)"
            )

        if self.guard_workload_savings_hours == 0:
            guard_note = ""
        else:
            guard_note = (
                f"\n  Guard workload reduction: "
                f"{self.guard_workload_savings_hours:,.0f} h"
                f"\n    → {self.guard_workload_savings_rub:,.0f} ₽ "
                f"(assumption scenario)"
            )

        if self.card_replacement_savings_rub == 0:
            card_note = ""
        else:
            card_note = (
                f"\n  Card replacement reduction: "
                f"{self.card_replacement_savings_rub:,.0f} ₽ (assumption scenario)"
            )
        payback_str = (
            f"{self.payback_period_years:.3f} years "
            f"({self.payback_period_years * 365:.0f} days)"
            if self.payback_period_years is not None
            else "N/A (negative net benefit)"
        )

        return f"""Economics Summary
=================

CAPEX (calculated from given parameters): {self.capex_rub:,.0f} ₽

Annual OPEX (from assumptions): {self.annual_opex_rub:,.0f} ₽

Annual Benefits (calculated):
  Direct passage time savings: {self.passage_time_savings_hours:,.0f} h
    → {self.passage_time_savings_rub:,.0f} ₽{queue_note}{guard_note}{card_note}

FRR Impact (calculated cost from assumption):
  Time loss from false rejects: {self.frr_time_loss_hours:,.0f} h
    → {self.frr_time_loss_rub:,.0f} ₽

Annual Gross Benefit (calculated): {self.annual_gross_benefit_rub:,.0f} ₽
Annual Net Benefit (calculated): {self.annual_net_benefit_rub:,.0f} ₽

Payback Period (calculated): {payback_str}
"""


def calculate(
    given: GivenParameters | None = None,
    assumptions: Assumptions | None = None,
) -> EconomicsResult:
    """Calculate economic effect of face-recognition access control system.

    Args:
        given: Given task parameters (uses defaults if None)
        assumptions: Explicit assumptions (uses defaults if None)

    Returns:
        EconomicsResult with detailed breakdown

    All inputs are labeled as given or assumed. Results are labeled as calculated.
    """
    if given is None:
        given = GivenParameters()
    if assumptions is None:
        assumptions = Assumptions()

    # CAPEX (calculated from given)
    capex = (
        given.entrances * given.edge_gpu_cost_per_entrance_rub
        + given.entrances * given.cameras_per_entrance * given.camera_cost_rub
    )

    # Annual OPEX (calculated from assumptions)
    annual_opex = (assumptions.monthly_maintenance_rub + assumptions.monthly_operations_rub) * 12

    # 1. Direct passage time savings (calculated)
    passage_time_saved_per_passage = (
        given.current_passage_time_seconds - assumptions.target_face_passage_time_seconds
    )
    annual_passage_seconds_saved = (
        passage_time_saved_per_passage
        * given.passages_per_day
        * given.working_days_per_year
    )
    passage_time_savings_hours = annual_passage_seconds_saved / 3600
    passage_time_savings_rub = (
        passage_time_savings_hours * given.employee_cost_per_minute_rub * 60
    )

    # 2. Queue time savings (calculated from assumption scenario)
    peak_passages_per_day = given.passages_per_day * given.peak_percentage
    annual_queue_seconds_saved = (
        assumptions.queue_time_reduction_seconds
        * peak_passages_per_day
        * given.working_days_per_year
    )
    queue_time_savings_hours = annual_queue_seconds_saved / 3600
    queue_time_savings_rub = (
        queue_time_savings_hours * given.employee_cost_per_minute_rub * 60
    )

    # 3. Guard workload reduction (calculated from assumption scenario)
    if assumptions.target_manual_cases_per_day is not None:
        guard_minutes_saved_per_day = (
            given.manual_cases_per_day - assumptions.target_manual_cases_per_day
        ) * given.manual_case_duration_minutes
        guard_workload_savings_hours = (
            guard_minutes_saved_per_day * given.working_days_per_year / 60
        )
        guard_workload_savings_rub = (
            guard_workload_savings_hours * given.employee_cost_per_minute_rub * 60
        )
    else:
        guard_workload_savings_hours = 0
        guard_workload_savings_rub = 0

    # 4. Card replacement reduction (calculated from assumption scenario)
    card_replacement_savings_rub = (
        given.card_replacements_per_year
        * assumptions.card_replacement_reduction_fraction
        * given.card_replacement_cost_rub
    )

    # 5. FRR impact (calculated cost from assumption)
    frr_cases_per_day = given.passages_per_day * assumptions.target_frr
    annual_frr_seconds_lost = (
        frr_cases_per_day
        * assumptions.frr_retry_delay_seconds
        * given.working_days_per_year
    )
    frr_time_loss_hours = annual_frr_seconds_lost / 3600
    frr_time_loss_rub = (
        frr_time_loss_hours * given.employee_cost_per_minute_rub * 60
    )

    # Totals (calculated)
    annual_gross_benefit = (
        passage_time_savings_rub
        + queue_time_savings_rub
        + guard_workload_savings_rub
        + card_replacement_savings_rub
    )

    annual_net_benefit = annual_gross_benefit - frr_time_loss_rub - annual_opex

    payback_years = capex / annual_net_benefit if annual_net_benefit > 0 else None

    return EconomicsResult(
        capex_rub=capex,
        annual_opex_rub=annual_opex,
        passage_time_savings_hours=passage_time_savings_hours,
        passage_time_savings_rub=passage_time_savings_rub,
        queue_time_savings_hours=queue_time_savings_hours,
        queue_time_savings_rub=queue_time_savings_rub,
        guard_workload_savings_hours=guard_workload_savings_hours,
        guard_workload_savings_rub=guard_workload_savings_rub,
        card_replacement_savings_rub=card_replacement_savings_rub,
        frr_time_loss_hours=frr_time_loss_hours,
        frr_time_loss_rub=frr_time_loss_rub,
        annual_gross_benefit_rub=annual_gross_benefit,
        annual_net_benefit_rub=annual_net_benefit,
        payback_period_years=payback_years,
    )


def print_scenarios() -> None:
    """Print multiple economic scenarios with different assumptions."""
    print("Economic Scenarios")
    print("=" * 80)
    print()
    print("NOTE: ML decision latency ≤1s is a technical requirement.")
    print("Total face passage time (approach to turnstile open) is scenario-assumed.")
    print()

    # Downside: 5 seconds face passage
    print("DOWNSIDE SCENARIO: 5s face passage time")
    print("-" * 80)
    print("Assumption: Total face passage = 5s (6s→5s, 1s savings)")
    print("No queue time benefit modeled")
    downside = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=5.0,
            queue_time_reduction_seconds=0.0,
        )
    )
    print(downside)

    # Base case: 4 seconds face passage
    print("\nBASE CASE: 4s face passage time")
    print("-" * 80)
    print("Assumption: Total face passage = 4s (6s→4s, 2s savings)")
    print("No queue time benefit modeled")
    base = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=0.0,
        )
    )
    print(base)

    # Upside: 3 seconds face passage
    print("\nUPSIDE SCENARIO: 3s face passage time")
    print("-" * 80)
    print("Assumption: Total face passage = 3s (6s→3s, 3s savings)")
    print("No queue time benefit modeled")
    upside = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=3.0,
            queue_time_reduction_seconds=0.0,
        )
    )
    print(upside)

    # Queue sensitivity (base case + queue)
    print("\nQUEUE SENSITIVITY (base case + 30s queue reduction)")
    print("-" * 80)
    print("Assumption: 4s face passage + 30s peak queue reduction")
    base_with_queue = calculate(
        assumptions=Assumptions(
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=30.0,
        )
    )
    print(base_with_queue)


def print_frr_sensitivity() -> None:
    """Print sensitivity analysis for different FRR values."""
    print("\nFRR Sensitivity Analysis (Base Case: 4s face passage, no queue benefit)")
    print("=" * 80)
    print(
        f"{'FRR':<8} {'FRR Loss (h)':<15} {'FRR Loss (₽)':<15} "
        f"{'Net Benefit (₽)':<20} {'Payback (days)':<15}"
    )
    print("-" * 80)

    for frr in [0.01, 0.03, 0.05, 0.10]:
        assumptions = Assumptions(
            target_frr=frr,
            target_face_passage_time_seconds=4.0,
            queue_time_reduction_seconds=0.0,
        )
        result = calculate(assumptions=assumptions)
        payback_days = (
            result.payback_period_years * 365
            if result.payback_period_years
            else float("inf")
        )
        print(
            f"{frr:<8.1%} {result.frr_time_loss_hours:<15,.0f} "
            f"{result.frr_time_loss_rub:<15,.0f} "
            f"{result.annual_net_benefit_rub:<20,.0f} {payback_days:<15.0f}"
        )


if __name__ == "__main__":
    print_scenarios()
    print_frr_sensitivity()
