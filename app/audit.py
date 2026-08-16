"""Append-only JSONL-аудит для минимального PoC."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.models import AccessContext, AccessDecision, AccessEvent, CvSignals
from app.turnstile import TurnstileResult


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    decision_id: str
    audit_id: str
    captured_at: str
    gate_id: str
    camera_id: str
    employee_id: str | None
    decision: str
    reasons: tuple[str, ...]
    turnstile_action: str
    side_effect_allowed: bool
    requires_human_review: bool
    degraded_mode: bool
    command_id: str | None
    command_applied: bool
    command_duplicate: bool
    model_version: str
    index_version: str
    policy_version: str
    quality: str
    liveness: str
    match: str
    next_action: str


def build_audit_record(
    event: AccessEvent,
    signals: CvSignals,
    context: AccessContext,
    decision: AccessDecision,
    turnstile_result: TurnstileResult | None,
) -> AuditRecord:
    return AuditRecord(
        event_id=event.event_id,
        decision_id=decision.decision_id,
        audit_id=decision.audit_id,
        captured_at=event.captured_at,
        gate_id=event.gate_id,
        camera_id=event.camera_id,
        employee_id=decision.employee_id,
        decision=decision.decision.value,
        reasons=decision.reasons,
        turnstile_action=decision.turnstile_action.value,
        side_effect_allowed=decision.side_effect_allowed,
        requires_human_review=decision.requires_human_review,
        degraded_mode=decision.degraded_mode,
        command_id=decision.command_id,
        command_applied=turnstile_result.applied if turnstile_result else False,
        command_duplicate=turnstile_result.duplicate if turnstile_result else False,
        model_version=context.model_version,
        index_version=context.index_version,
        policy_version=context.policy_version,
        quality=signals.quality.value,
        liveness=signals.liveness.value,
        match=signals.match.value,
        next_action=decision.next_action,
    )


def append_jsonl(path: Path, record: AuditRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
