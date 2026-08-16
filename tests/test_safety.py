from app.decision import decide
from app.demo import run_demo
from app.models import (
    AccessContext,
    AccessEvent,
    AccessState,
    CvSignals,
    LivenessState,
    MatchState,
    PolicyState,
    QualityState,
)


def _event(event_id: str) -> AccessEvent:
    return AccessEvent(event_id, "gate-1", "cam-1a", "2026-07-31T09:00:00Z")


def _strong_signals(*, liveness: LivenessState = LivenessState.PASS) -> CvSignals:
    return CvSignals(
        True,
        QualityState.PASS,
        liveness,
        MatchState.STRONG_UNIQUE,
        "emp-1",
    )


def test_low_quality_uses_fast_fallback_without_open() -> None:
    result = run_demo("low_quality")
    assert result.decision == "deny"
    assert result.side_effect_allowed is False
    assert result.requires_human_review is False
    assert result.next_action == "retry_or_card_fallback"


def test_spoof_never_opens_turnstile() -> None:
    result = run_demo("spoof")
    assert result.decision == "deny"
    assert result.side_effect_allowed is False
    assert result.turnstile_command == "closed"
    assert result.requires_human_review is True
    assert "spoof_suspected" in result.reasons


def test_offline_with_stale_policy_never_auto_allows() -> None:
    result = run_demo("offline")
    assert result.decision == "manual_review"
    assert result.side_effect_allowed is False
    assert result.turnstile_command == "closed"
    assert result.degraded_mode is True
    assert "policy_stale_or_unknown" in result.reasons


def test_revoked_employee_never_opens_turnstile() -> None:
    result = run_demo("revoked")
    assert result.decision == "deny"
    assert result.side_effect_allowed is False
    assert result.turnstile_command == "closed"
    assert "access_revoked" in result.reasons


def test_model_unavailable_fails_closed() -> None:
    decision = decide(
        _event("e-model-down"),
        _strong_signals(),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE, model_available=False),
    )
    assert decision.side_effect_allowed is False
    assert decision.turnstile_action.value == "closed"


def test_ann_unavailable_fails_closed() -> None:
    decision = decide(
        _event("e-ann-down"),
        _strong_signals(),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE, ann_available=False),
    )
    assert decision.side_effect_allowed is False
    assert decision.turnstile_action.value == "closed"


def test_unknown_policy_fails_closed() -> None:
    decision = decide(
        _event("e-policy-unknown"),
        _strong_signals(),
        AccessContext(PolicyState.UNKNOWN, AccessState.ACTIVE),
    )
    assert decision.side_effect_allowed is False
    assert decision.turnstile_action.value == "closed"


def test_uncertain_liveness_requires_review_and_stays_closed() -> None:
    decision = decide(
        _event("e-live-uncertain"),
        _strong_signals(liveness=LivenessState.UNCERTAIN),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE),
    )
    assert decision.decision.value == "manual_review"
    assert decision.side_effect_allowed is False
    assert decision.turnstile_action.value == "closed"
