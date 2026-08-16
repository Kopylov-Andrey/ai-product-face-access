from itertools import product

from app.decision import decide
from app.demo import run_demo
from app.models import (
    AccessContext,
    AccessEvent,
    AccessState,
    CvSignals,
    Decision,
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


def test_face_not_detected_fails_closed() -> None:
    decision = decide(
        _event("e-no-face"),
        CvSignals(
            False,
            QualityState.PASS,
            LivenessState.PASS,
            MatchState.STRONG_UNIQUE,
            "emp-1",
        ),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE),
    )
    assert decision.decision == Decision.DENY
    assert decision.side_effect_allowed is False
    assert "face_not_detected" in decision.reasons


def test_quality_fail_fails_closed() -> None:
    decision = decide(
        _event("e-quality-fail"),
        CvSignals(
            True,
            QualityState.FAIL,
            LivenessState.PASS,
            MatchState.STRONG_UNIQUE,
            "emp-1",
        ),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE),
    )
    assert decision.decision == Decision.DENY
    assert decision.side_effect_allowed is False
    assert decision.next_action == "retry_or_card_fallback"


def test_no_match_fails_closed() -> None:
    decision = decide(
        _event("e-no-match"),
        CvSignals(True, QualityState.PASS, LivenessState.PASS, MatchState.NO_MATCH),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE),
    )
    assert decision.decision == Decision.DENY
    assert decision.side_effect_allowed is False
    assert "no_match" in decision.reasons


def test_unknown_access_state_requires_review() -> None:
    decision = decide(
        _event("e-access-unknown"),
        _strong_signals(),
        AccessContext(PolicyState.FRESH, AccessState.UNKNOWN),
    )
    assert decision.decision == Decision.MANUAL_REVIEW
    assert decision.side_effect_allowed is False
    assert "access_state_unknown" in decision.reasons


def test_identity_without_employee_id_never_opens() -> None:
    decision = decide(
        _event("e-no-employee"),
        CvSignals(
            True,
            QualityState.PASS,
            LivenessState.PASS,
            MatchState.STRONG_UNIQUE,
            None,
        ),
        AccessContext(PolicyState.FRESH, AccessState.ACTIVE),
    )
    assert decision.decision == Decision.MANUAL_REVIEW
    assert decision.side_effect_allowed is False
    assert "identity_not_proven" in decision.reasons


def test_exhaustive_state_space_only_valid_happy_path_can_open() -> None:
    """Перебрать все 7 776 комбинаций доменных состояний decision engine."""

    open_count = 0
    combinations = product(
        (False, True),
        tuple(QualityState),
        tuple(LivenessState),
        tuple(MatchState),
        (None, "emp-1"),
        tuple(PolicyState),
        tuple(AccessState),
        (False, True),
        (False, True),
        (False, True),
    )

    for index, (
        face_detected,
        quality,
        liveness,
        match,
        employee_id,
        policy_state,
        access_state,
        model_available,
        ann_available,
        network_online,
    ) in enumerate(combinations):
        event = AccessEvent(
            event_id=f"e-exhaustive-{index}",
            gate_id="gate-1",
            camera_id="cam-1",
            captured_at="2026-07-31T09:00:00Z",
            network_online=network_online,
        )
        signals = CvSignals(
            face_detected=face_detected,
            quality=quality,
            liveness=liveness,
            match=match,
            employee_id=employee_id,
        )
        context = AccessContext(
            policy_state=policy_state,
            access_state=access_state,
            model_available=model_available,
            ann_available=ann_available,
        )
        decision = decide(event, signals, context)

        valid_open = (
            face_detected
            and quality == QualityState.PASS
            and liveness == LivenessState.PASS
            and match == MatchState.STRONG_UNIQUE
            and employee_id is not None
            and policy_state == PolicyState.FRESH
            and access_state == AccessState.ACTIVE
            and model_available
            and ann_available
        )

        assert decision.side_effect_allowed is valid_open
        if valid_open:
            assert decision.decision == Decision.ALLOW
            assert decision.command_id is not None
            open_count += 1
        else:
            assert decision.decision != Decision.ALLOW
            assert decision.command_id is None

    # Две допустимые комбинации отличаются только наличием WAN при FRESH snapshot.
    assert open_count == 2
