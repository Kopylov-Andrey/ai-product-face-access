"""Идемпотентная симуляция адаптера турникета."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TurnstileResult:
    command_id: str
    applied: bool
    duplicate: bool
    state: str


@dataclass
class TurnstileSimulator:
    """Хранит применённые command_id и не повторяет физический side effect."""

    _results: dict[str, TurnstileResult] = field(default_factory=dict)
    open_count: int = 0

    def open(self, command_id: str) -> TurnstileResult:
        previous = self._results.get(command_id)
        if previous is not None:
            return TurnstileResult(
                command_id=command_id,
                applied=False,
                duplicate=True,
                state=previous.state,
            )

        self.open_count += 1
        result = TurnstileResult(
            command_id=command_id,
            applied=True,
            duplicate=False,
            state="open_command_applied",
        )
        self._results[command_id] = result
        return result
