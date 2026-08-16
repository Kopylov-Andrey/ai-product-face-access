from scripts.load_smoke import percentile_ms, run_profile


def test_percentile_ms_uses_nearest_rank() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert percentile_ms(values, 50) == 2.0
    assert percentile_ms(values, 95) == 4.0
    assert percentile_ms([], 95) == 0.0


def test_short_load_profile_preserves_fail_safe_behavior() -> None:
    result = run_profile("stress", duration_s=0.1, workers=4)

    assert result.errors == 0
    assert result.unsafe_open_count == 0
    assert result.audit_records == result.requests
    assert result.requests >= 6
