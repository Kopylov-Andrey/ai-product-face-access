from app.demo import run_demo


def test_happy_path_allows_side_effect() -> None:
    result = run_demo("happy")
    assert result.decision == "allow"
    assert result.side_effect_allowed is True


def test_risky_path_fails_safe() -> None:
    result = run_demo("risky")
    assert result.decision != "allow"
    assert result.side_effect_allowed is False
