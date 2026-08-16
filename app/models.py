"""Доменные модели минимального PoC контроля доступа.

CV/ML-сигналы в PoC синтетические: этот модуль проверяет правила принятия
решения и инварианты безопасности, а не качество реальной модели распознавания.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QualityState(StrEnum):
    PASS = "pass"
    RETRY = "retry"
    FAIL = "fail"


class LivenessState(StrEnum):
    PASS = "pass"
    UNCERTAIN = "uncertain"
    SPOOF = "spoof"


class MatchState(StrEnum):
    STRONG_UNIQUE = "strong_unique"
    BORDERLINE = "borderline"
    NO_MATCH = "no_match"


class PolicyState(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class AccessState(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    MANUAL_REVIEW = "manual_review"


class TurnstileAction(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class AccessEvent:
    event_id: str
    gate_id: str
    camera_id: str
    captured_at: str
    network_online: bool = True


@dataclass(frozen=True)
class CvSignals:
    face_detected: bool
    quality: QualityState
    liveness: LivenessState
    match: MatchState
    employee_id: str | None = None


@dataclass(frozen=True)
class AccessContext:
    policy_state: PolicyState
    access_state: AccessState
    model_available: bool = True
    ann_available: bool = True
    model_version: str = "demo-model-v1"
    index_version: str = "demo-index-v1"
    policy_version: str = "demo-policy-v1"


@dataclass(frozen=True)
class AccessDecision:
    event_id: str
    decision_id: str
    decision: Decision
    employee_id: str | None
    reasons: tuple[str, ...]
    turnstile_action: TurnstileAction
    side_effect_allowed: bool
    requires_human_review: bool
    degraded_mode: bool
    command_id: str | None
    audit_id: str
    next_action: str
