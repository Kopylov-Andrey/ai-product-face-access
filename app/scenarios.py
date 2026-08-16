"""Синтетические сценарии, соответствующие условиям задания."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import (
    AccessContext,
    AccessEvent,
    AccessState,
    CvSignals,
    LivenessState,
    MatchState,
    PolicyState,
    QualityState,
)


@dataclass(frozen=True)
class Scenario:
    event: AccessEvent
    signals: CvSignals
    context: AccessContext


def _event(event_id: str, gate: str, camera: str, *, online: bool = True) -> AccessEvent:
    return AccessEvent(
        event_id=event_id,
        gate_id=gate,
        camera_id=camera,
        captured_at="2026-07-31T09:00:00Z",
        network_online=online,
    )


def get_scenario(name: str) -> Scenario:
    scenarios = {
        "happy": Scenario(
            event=_event("e-1001", "gate-2", "cam-2a"),
            signals=CvSignals(
                face_detected=True,
                quality=QualityState.PASS,
                liveness=LivenessState.PASS,
                match=MatchState.STRONG_UNIQUE,
                employee_id="emp-4821",
            ),
            context=AccessContext(
                policy_state=PolicyState.FRESH,
                access_state=AccessState.ACTIVE,
            ),
        ),
        "risky": Scenario(
            event=_event("e-1004", "gate-2", "cam-2b"),
            signals=CvSignals(
                face_detected=True,
                quality=QualityState.PASS,
                liveness=LivenessState.PASS,
                match=MatchState.BORDERLINE,
                employee_id="emp-4821",
            ),
            context=AccessContext(
                policy_state=PolicyState.FRESH,
                access_state=AccessState.ACTIVE,
            ),
        ),
        "low_quality": Scenario(
            event=_event("e-1002", "gate-1", "cam-1b"),
            signals=CvSignals(
                face_detected=True,
                quality=QualityState.RETRY,
                liveness=LivenessState.PASS,
                match=MatchState.NO_MATCH,
            ),
            context=AccessContext(
                policy_state=PolicyState.FRESH,
                access_state=AccessState.UNKNOWN,
            ),
        ),
        "spoof": Scenario(
            event=_event("e-1003", "gate-3", "cam-3a"),
            signals=CvSignals(
                face_detected=True,
                quality=QualityState.PASS,
                liveness=LivenessState.SPOOF,
                match=MatchState.STRONG_UNIQUE,
                employee_id="emp-4821",
            ),
            context=AccessContext(
                policy_state=PolicyState.FRESH,
                access_state=AccessState.ACTIVE,
            ),
        ),
        "offline": Scenario(
            event=_event("e-1005", "gate-1", "cam-1a", online=False),
            signals=CvSignals(
                face_detected=True,
                quality=QualityState.PASS,
                liveness=LivenessState.PASS,
                match=MatchState.STRONG_UNIQUE,
                employee_id="emp-4821",
            ),
            context=AccessContext(
                policy_state=PolicyState.STALE,
                access_state=AccessState.ACTIVE,
            ),
        ),
        "revoked": Scenario(
            event=_event("e-1006", "gate-1", "cam-1a"),
            signals=CvSignals(
                face_detected=True,
                quality=QualityState.PASS,
                liveness=LivenessState.PASS,
                match=MatchState.STRONG_UNIQUE,
                employee_id="emp-revoked",
            ),
            context=AccessContext(
                policy_state=PolicyState.FRESH,
                access_state=AccessState.REVOKED,
            ),
        ),
    }
    try:
        return scenarios[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported scenario: {name}") from exc
