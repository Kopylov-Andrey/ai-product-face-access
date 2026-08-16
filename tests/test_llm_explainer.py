from types import SimpleNamespace

import pytest

from app.demo import run_demo
from app.llm_explainer import (
    ExplainerError,
    build_messages,
    explain_incident,
    incident_payload,
)


class FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(
            content=(
                "Система не смогла достаточно уверенно подтвердить вашу личность. "
                "Обратитесь к сотруднику охраны для ручной проверки."
            )
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_payload_excludes_employee_scores_and_internal_reason_codes() -> None:
    result = run_demo("risky", audit_path=None)
    payload = incident_payload(result)
    serialized = str(payload)

    assert result.employee_id not in serialized
    assert "score" not in serialized.lower()
    assert "threshold" not in serialized.lower()
    assert "ambiguous_match" not in serialized
    assert "insufficient_candidate_margin" not in serialized
    assert payload["turnstile"] == "CLOSED"
    assert "личность" in str(payload["safe_reason"])


def test_messages_freeze_decision_and_target_employee_explanation() -> None:
    result = run_demo("spoof", audit_path=None)
    messages = build_messages(result)

    system = messages[0]["content"]
    assert "для сотрудника" in system
    assert "неизменяемым" in system
    assert "никогда не предлагай открыть турникет" in system.lower()
    assert "не повторяй дословно" in system.lower()
    assert "spoof_suspected" not in messages[1]["content"]


def test_explainer_uses_optional_client_without_changing_result() -> None:
    result = run_demo("risky", audit_path=None)
    client = FakeClient()

    explanation = explain_incident(result, client=client, model="test-model")

    assert explanation.model == "test-model"
    assert "обратитесь к сотруднику охраны" in explanation.text.lower()
    assert result.decision == "manual_review"
    assert result.side_effect_allowed is False
    assert client.completions.kwargs["model"] == "test-model"


def test_explainer_rejects_allow_event() -> None:
    result = run_demo("happy", audit_path=None)

    with pytest.raises(ExplainerError, match="только для закрытых"):
        explain_incident(result, client=FakeClient(), model="test-model")
