from app.demo import run_demo


def test_happy_path_allows_and_opens() -> None:
    result = run_demo("happy")
    assert result.decision == "allow"
    assert result.side_effect_allowed is True
    assert result.turnstile_command == "open"
    assert result.turnstile_applied is True
    assert result.requires_human_review is False


def test_risky_path_fails_safe() -> None:
    result = run_demo("risky")
    assert result.decision == "manual_review"
    assert result.side_effect_allowed is False
    assert result.turnstile_command == "closed"
    assert result.turnstile_applied is False
    assert result.requires_human_review is True
