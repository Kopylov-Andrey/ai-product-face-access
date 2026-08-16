import json

from app.demo import run_demo


def test_risky_event_is_written_to_audit_with_reason(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    result = run_demo("risky", audit_path=path)

    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert record["event_id"] == result.event_id
    assert record["decision"] == "manual_review"
    assert record["turnstile_action"] == "closed"
    assert record["side_effect_allowed"] is False
    assert "ambiguous_match" in record["reasons"]
    assert record["command_applied"] is False


def test_happy_event_audit_records_applied_open(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    run_demo("happy", audit_path=path)

    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert record["decision"] == "allow"
    assert record["turnstile_action"] == "open"
    assert record["side_effect_allowed"] is True
    assert record["command_applied"] is True
