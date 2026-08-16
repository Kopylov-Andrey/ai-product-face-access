"""Generic reproducible economics helper.

No case-specific numbers are embedded. Fill inputs only after receiving the real task.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EconomicsInput:
    events_per_day: float
    seconds_saved_per_event: float
    working_days_per_year: int
    hourly_cost: float
    adoption: float
    capex: float
    annual_opex: float


@dataclass(frozen=True)
class EconomicsResult:
    annual_hours_saved: float
    annual_gross_value: float
    annual_net_value: float
    payback_years: float | None


def calculate(data: EconomicsInput) -> EconomicsResult:
    if not 0 <= data.adoption <= 1:
        raise ValueError("adoption must be between 0 and 1")
    if min(
        data.events_per_day,
        data.seconds_saved_per_event,
        data.working_days_per_year,
        data.hourly_cost,
        data.capex,
        data.annual_opex,
    ) < 0:
        raise ValueError("economics inputs must be non-negative")

    annual_seconds = (
        data.events_per_day
        * data.seconds_saved_per_event
        * data.working_days_per_year
        * data.adoption
    )
    annual_hours = annual_seconds / 3600
    gross = annual_hours * data.hourly_cost
    net = gross - data.annual_opex
    payback = data.capex / net if net > 0 else None
    return EconomicsResult(annual_hours, gross, net, payback)
