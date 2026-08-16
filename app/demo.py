"""Минимальный end-to-end PoC принятия решения о проходе."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.audit import append_jsonl, build_audit_record
from app.decision import decide
from app.models import Decision, TurnstileAction
from app.scenarios import get_scenario
from app.turnstile import TurnstileSimulator


@dataclass(frozen=True)
class DemoResult:
    scenario: str
    event_id: str
    decision: str
    employee_id: str | None
    reasons: tuple[str, ...]
    turnstile_command: str
    side_effect_allowed: bool
    turnstile_applied: bool
    requires_human_review: bool
    degraded_mode: bool
    next_action: str
    audit_id: str


def run_demo(
    scenario: str,
    *,
    audit_path: Path | None = None,
    turnstile: TurnstileSimulator | None = None,
) -> DemoResult:
    data = get_scenario(scenario)
    decision = decide(data.event, data.signals, data.context)
    simulator = turnstile or TurnstileSimulator()

    turnstile_result = None
    if decision.side_effect_allowed:
        if decision.decision != Decision.ALLOW:
            raise AssertionError("side effect is allowed only for ALLOW")
        if decision.turnstile_action != TurnstileAction.OPEN or decision.command_id is None:
            raise AssertionError("ALLOW must carry an OPEN command_id")
        turnstile_result = simulator.open(decision.command_id)

    record = build_audit_record(
        data.event,
        data.signals,
        data.context,
        decision,
        turnstile_result,
    )
    if audit_path is not None:
        append_jsonl(audit_path, record)

    return DemoResult(
        scenario=scenario,
        event_id=decision.event_id,
        decision=decision.decision.value,
        employee_id=decision.employee_id,
        reasons=decision.reasons,
        turnstile_command=decision.turnstile_action.value,
        side_effect_allowed=decision.side_effect_allowed,
        turnstile_applied=turnstile_result.applied if turnstile_result else False,
        requires_human_review=decision.requires_human_review,
        degraded_mode=decision.degraded_mode,
        next_action=decision.next_action,
        audit_id=decision.audit_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="PoC контроля доступа по лицу")
    parser.add_argument(
        "--scenario",
        choices=("happy", "risky", "low_quality", "spoof", "offline", "revoked"),
        required=True,
    )
    parser.add_argument(
        "--audit-path",
        type=Path,
        default=Path("var/access_audit.jsonl"),
        help="JSONL-файл аудита; каталог var/ исключён из Git",
    )
    args = parser.parse_args()

    result = run_demo(args.scenario, audit_path=args.audit_path)
    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
