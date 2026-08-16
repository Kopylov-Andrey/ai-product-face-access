"""Детерминированный fail-safe движок решений для PoC."""

from __future__ import annotations

import hashlib

from app.models import (
    AccessContext,
    AccessDecision,
    AccessEvent,
    AccessState,
    CvSignals,
    Decision,
    LivenessState,
    MatchState,
    PolicyState,
    QualityState,
    TurnstileAction,
)


def _stable_id(prefix: str, event_id: str) -> str:
    digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _closed_decision(
    event: AccessEvent,
    *,
    decision: Decision,
    reasons: tuple[str, ...],
    employee_id: str | None,
    requires_human_review: bool,
    degraded_mode: bool,
    next_action: str,
) -> AccessDecision:
    return AccessDecision(
        event_id=event.event_id,
        decision_id=_stable_id("d", event.event_id),
        decision=decision,
        employee_id=employee_id,
        reasons=reasons,
        turnstile_action=TurnstileAction.CLOSED,
        side_effect_allowed=False,
        requires_human_review=requires_human_review,
        degraded_mode=degraded_mode,
        command_id=None,
        audit_id=_stable_id("a", event.event_id),
        next_action=next_action,
    )


def decide(event: AccessEvent, signals: CvSignals, context: AccessContext) -> AccessDecision:
    """Принять решение без внешних вызовов и недетерминированных компонентов.

    Единственный путь к OPEN: доступные модель и ANN, обнаруженное лицо,
    приемлемое качество, успешный liveness/PAD, сильное уникальное совпадение,
    FRESH-политика и ACTIVE-доступ сотрудника.
    """

    degraded = (not event.network_online) or context.policy_state != PolicyState.FRESH

    if not context.model_available:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("model_unavailable",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=True,
            next_action="safe_fallback_or_guard_review",
        )

    if not context.ann_available:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("ann_unavailable",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=True,
            next_action="safe_fallback_or_guard_review",
        )

    if not signals.face_detected:
        return _closed_decision(
            event,
            decision=Decision.DENY,
            reasons=("face_not_detected",),
            employee_id=None,
            requires_human_review=False,
            degraded_mode=degraded,
            next_action="retry_or_card_fallback",
        )

    if signals.quality != QualityState.PASS:
        reason = "quality_retry" if signals.quality == QualityState.RETRY else "quality_failed"
        return _closed_decision(
            event,
            decision=Decision.DENY,
            reasons=(reason,),
            employee_id=signals.employee_id,
            requires_human_review=False,
            degraded_mode=degraded,
            next_action="retry_or_card_fallback",
        )

    if signals.liveness == LivenessState.SPOOF:
        return _closed_decision(
            event,
            decision=Decision.DENY,
            reasons=("spoof_suspected",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=degraded,
            next_action="security_review",
        )

    if signals.liveness == LivenessState.UNCERTAIN:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("liveness_uncertain",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=degraded,
            next_action="guard_review",
        )

    if context.policy_state != PolicyState.FRESH:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("policy_stale_or_unknown",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=True,
            next_action="safe_fallback_or_guard_review",
        )

    if context.access_state == AccessState.REVOKED:
        return _closed_decision(
            event,
            decision=Decision.DENY,
            reasons=("access_revoked",),
            employee_id=signals.employee_id,
            requires_human_review=False,
            degraded_mode=degraded,
            next_action="access_denied",
        )

    if context.access_state == AccessState.UNKNOWN:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("access_state_unknown",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=degraded,
            next_action="guard_review",
        )

    if signals.match == MatchState.NO_MATCH:
        return _closed_decision(
            event,
            decision=Decision.DENY,
            reasons=("no_match",),
            employee_id=None,
            requires_human_review=False,
            degraded_mode=degraded,
            next_action="card_fallback_or_guard_review",
        )

    if signals.match == MatchState.BORDERLINE:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("ambiguous_match", "insufficient_candidate_margin"),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=degraded,
            next_action="guard_review",
        )

    if signals.match != MatchState.STRONG_UNIQUE or signals.employee_id is None:
        return _closed_decision(
            event,
            decision=Decision.MANUAL_REVIEW,
            reasons=("identity_not_proven",),
            employee_id=signals.employee_id,
            requires_human_review=True,
            degraded_mode=degraded,
            next_action="guard_review",
        )

    return AccessDecision(
        event_id=event.event_id,
        decision_id=_stable_id("d", event.event_id),
        decision=Decision.ALLOW,
        employee_id=signals.employee_id,
        reasons=("quality_ok", "liveness_ok", "strong_unique_match", "access_active"),
        turnstile_action=TurnstileAction.OPEN,
        side_effect_allowed=True,
        requires_human_review=False,
        degraded_mode=degraded,
        command_id=_stable_id("cmd", event.event_id),
        audit_id=_stable_id("a", event.event_id),
        next_action="open_turnstile",
    )
