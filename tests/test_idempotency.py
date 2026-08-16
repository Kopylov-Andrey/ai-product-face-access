from app.demo import run_demo
from app.turnstile import TurnstileSimulator


def test_duplicate_event_does_not_open_twice() -> None:
    turnstile = TurnstileSimulator()

    first = run_demo("happy", turnstile=turnstile)
    second = run_demo("happy", turnstile=turnstile)

    assert first.turnstile_applied is True
    assert second.turnstile_applied is False
    assert turnstile.open_count == 1
