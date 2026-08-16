from app.demo import run_demo


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
