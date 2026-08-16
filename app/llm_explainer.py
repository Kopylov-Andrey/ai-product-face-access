"""Опциональное LLM-пояснение для сотрудника после закрытого решения.

Модуль намеренно находится вне критического пути доступа: он не формирует
ALLOW/DENY, не меняет команду турникету и может быть полностью недоступен без
влияния на основной PoC.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from app.demo import DemoResult

DEFAULT_BASE_URL = "https://caila.io/api/adapters/openai"
DEFAULT_MODEL = "just-ai/google-gemini/gemini-3.5-flash"

SAFE_REASON_TEXT = {
    "ambiguous_match": "личность не подтверждена с достаточной уверенностью",
    "insufficient_candidate_margin": "несколько совпадений слишком близки",
    "spoof_suspected": "биометрическая проверка не пройдена",
    "policy_stale_or_unknown": "актуальность права доступа временно не подтверждена",
    "access_revoked": "право доступа неактивно",
    "quality_retry": "качество кадра недостаточно для надёжной проверки",
    "face_not_detected": "лицо не удалось корректно обнаружить в кадре",
    "liveness_uncertain": "проверка живости не дала однозначного результата",
    "liveness_failed": "биометрическая проверка не пройдена",
    "no_match": "личность не удалось подтвердить",
    "identity_not_proven": "личность не подтверждена с достаточной уверенностью",
}

SAFE_ACTION_TEXT = {
    "guard_review": "обратитесь к сотруднику охраны для ручной проверки",
    "security_review": "обратитесь к сотруднику охраны или службе безопасности",
    "safe_fallback_or_guard_review": (
        "используйте предусмотренный резервный способ прохода или обратитесь к охране"
    ),
    "access_denied": "обратитесь к ответственному за права доступа или к сотруднику охраны",
    "retry_or_card_fallback": "повторите попытку перед камерой или используйте карту",
    "card_fallback_or_guard_review": "используйте карту или обратитесь к сотруднику охраны",
}


class ExplainerError(RuntimeError):
    """Ошибка необязательного LLM-пояснения."""


@dataclass(frozen=True)
class IncidentExplanation:
    """Результат генерации безопасного пояснения для сотрудника."""

    text: str
    model: str
    latency_seconds: float


def explainer_configured() -> bool:
    """Проверить наличие локального API-ключа без его чтения/вывода."""

    return bool((os.getenv("CAILA_API_KEY") or "").strip())


def incident_payload(result: DemoResult) -> dict[str, object]:
    """Сформировать минимальный обезличенный контекст для LLM.

    В payload нет employee_id, биометрических изображений, match-score,
    внутренних порогов, списка кандидатов и внутренних reason-кодов.
    """

    explanations = []
    for reason in result.reasons:
        safe_text = SAFE_REASON_TEXT.get(reason)
        if safe_text and safe_text not in explanations:
            explanations.append(safe_text)

    return {
        "decision": result.decision,
        "safe_reason": explanations or ["автоматический проход сейчас недоступен"],
        "requires_human_review": result.requires_human_review,
        "degraded_mode": result.degraded_mode,
        "recommended_action": SAFE_ACTION_TEXT.get(
            result.next_action,
            "следуйте инструкции сотрудника охраны",
        ),
        "turnstile": "CLOSED",
    }


def build_messages(result: DemoResult) -> list[dict[str, str]]:
    """Создать ограниченный prompt: пояснение пользователю, но не новое решение."""

    if result.side_effect_allowed:
        raise ExplainerError(
            "LLM-пояснение предназначено только для закрытых/ручных инцидентов."
        )

    payload = json.dumps(incident_payload(result), ensure_ascii=False)
    return [
        {
            "role": "system",
            "content": (
                "Ты формируешь короткое пояснение для сотрудника, чей проход "
                "не был автоматически выполнен. Решение уже принято "
                "детерминированной системой и является неизменяемым. Напиши "
                "ровно 2 коротких предложения простым русским языком: сначала "
                "объясни причину понятными словами, затем укажи безопасное "
                "следующее действие. Обращайся нейтрально, без канцелярита. "
                "Не повторяй дословно текст интерфейса, не перечисляй внутренние "
                "коды и не используй слова score, threshold, ANN, PAD, top-K. "
                "Не раскрывай детали антиспуфинга и не давай советов по обходу "
                "проверки. При CLOSED никогда не предлагай открыть турникет. "
                "Используй только переданные факты и не придумывай причины."
            ),
        },
        {
            "role": "user",
            "content": f"Безопасный контекст события: {payload}",
        },
    ]


def _create_client(api_key: str, base_url: str) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ExplainerError(
            "Не установлен optional LLM-клиент. Выполните: "
            "python -m pip install -r requirements-llm.txt"
        ) from exc

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=20.0,
        max_retries=0,
    )


def explain_incident(
    result: DemoResult,
    *,
    client: Any | None = None,
    model: str | None = None,
) -> IncidentExplanation:
    """Сгенерировать необязательное пояснение без влияния на access decision."""

    if result.side_effect_allowed:
        raise ExplainerError(
            "LLM-пояснение предназначено только для закрытых/ручных инцидентов."
        )

    selected_model = (
        model
        or (os.getenv("CAILA_EXPLAINER_MODEL") or "").strip()
        or (os.getenv("CAILA_MODEL") or "").strip()
        or DEFAULT_MODEL
    )

    if client is None:
        api_key = (os.getenv("CAILA_API_KEY") or "").strip()
        if not api_key:
            raise ExplainerError("CAILA_API_KEY не задан в локальном окружении.")
        base_url = (
            (os.getenv("CAILA_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
        )
        client = _create_client(api_key, base_url)

    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=build_messages(result),
        )
    except Exception as exc:  # noqa: BLE001 - граница внешнего optional provider
        raise ExplainerError(f"LLM-провайдер недоступен: {type(exc).__name__}") from exc

    latency = time.perf_counter() - started
    if not getattr(response, "choices", None):
        raise ExplainerError("LLM-провайдер вернул ответ без choices.")

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ExplainerError("LLM-провайдер вернул пустое пояснение.")

    return IncidentExplanation(
        text=content,
        model=selected_model,
        latency_seconds=latency,
    )
