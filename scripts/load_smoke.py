"""Нагрузочный smoke-test decision/audit-контура PoC.

Тест не измеряет реальный CV/ML pipeline: detection, PAD, embedding и ANN в PoC
представлены детерминированными синтетическими сигналами. Цель скрипта — проверить
накладные расходы decision/audit-контура и убедиться, что fail-safe инварианты
сохраняются при конкурентной обработке событий.
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from app.audit import append_jsonl, build_audit_record
from app.decision import decide
from app.models import Decision, TurnstileAction
from app.scenarios import get_scenario
from app.turnstile import TurnstileSimulator

SCENARIO_CYCLE = (
    "happy",
    "risky",
    "spoof",
    "offline",
    "revoked",
    "low_quality",
)

PROFILE_RATES = {
    "baseline": 1.0,
    "burst": 3.0,
    "stress": 5.0,
}


@dataclass(frozen=True)
class Sample:
    scenario: str
    latency_ms: float
    decision: str
    unsafe_open: bool
    error: str | None = None


@dataclass(frozen=True)
class ProfileResult:
    profile: str
    offered_rate_eps: float
    duration_s: float
    requests: int
    errors: int
    throughput_eps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    decisions: dict[str, int]
    unsafe_open_count: int
    audit_records: int


def percentile_ms(values: list[float], percentile: float) -> float:
    """Вернуть percentile по nearest-rank; подходит для короткого smoke-test."""

    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100.0) * len(ordered)))
    return ordered[rank - 1]


def _execute_request(
    scenario_name: str,
    sequence: int,
    audit_path: Path,
    audit_lock: threading.Lock,
) -> Sample:
    started = time.perf_counter()
    try:
        scenario = get_scenario(scenario_name)
        event = replace(
            scenario.event,
            event_id=f"{scenario.event.event_id}-load-{sequence:06d}",
        )
        decision = decide(event, scenario.signals, scenario.context)

        turnstile_result = None
        if decision.side_effect_allowed:
            if decision.decision != Decision.ALLOW:
                raise AssertionError("side effect is allowed only for ALLOW")
            if decision.turnstile_action != TurnstileAction.OPEN:
                raise AssertionError("ALLOW must use OPEN")
            if decision.command_id is None:
                raise AssertionError("ALLOW must carry command_id")
            turnstile_result = TurnstileSimulator().open(decision.command_id)

        record = build_audit_record(
            event,
            scenario.signals,
            scenario.context,
            decision,
            turnstile_result,
        )
        with audit_lock:
            append_jsonl(audit_path, record)

        unsafe_open = (
            scenario_name != "happy"
            and decision.side_effect_allowed
            and decision.turnstile_action == TurnstileAction.OPEN
        )
        return Sample(
            scenario=scenario_name,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            decision=decision.decision.value,
            unsafe_open=unsafe_open,
        )
    except Exception as exc:  # noqa: BLE001
        return Sample(
            scenario=scenario_name,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            decision="error",
            unsafe_open=False,
            error=f"{type(exc).__name__}: {exc}",
        )


def run_profile(
    profile: str,
    *,
    duration_s: float = 6.0,
    workers: int = 8,
) -> ProfileResult:
    """Запустить rate-controlled профиль нагрузки."""

    try:
        rate = PROFILE_RATES[profile]
    except KeyError as exc:
        raise ValueError(f"Unknown profile: {profile}") from exc

    request_count = max(len(SCENARIO_CYCLE), math.ceil(rate * duration_s))
    interval_s = 1.0 / rate
    audit_lock = threading.Lock()

    with tempfile.TemporaryDirectory(prefix="face-access-load-") as temp_dir:
        audit_path = Path(temp_dir) / "audit.jsonl"
        started = time.perf_counter()
        futures = []

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for sequence in range(request_count):
                target_time = started + (sequence * interval_s)
                delay = target_time - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)

                scenario_name = SCENARIO_CYCLE[sequence % len(SCENARIO_CYCLE)]
                futures.append(
                    executor.submit(
                        _execute_request,
                        scenario_name,
                        sequence,
                        audit_path,
                        audit_lock,
                    )
                )

            samples = [future.result() for future in as_completed(futures)]

        elapsed_s = max(time.perf_counter() - started, 1e-9)
        audit_records = 0
        if audit_path.exists():
            audit_records = len(audit_path.read_text(encoding="utf-8").splitlines())

    latencies = [sample.latency_ms for sample in samples]
    errors = [sample for sample in samples if sample.error is not None]
    decisions = Counter(sample.decision for sample in samples if sample.error is None)

    return ProfileResult(
        profile=profile,
        offered_rate_eps=rate,
        duration_s=elapsed_s,
        requests=len(samples),
        errors=len(errors),
        throughput_eps=len(samples) / elapsed_s,
        p50_ms=percentile_ms(latencies, 50),
        p95_ms=percentile_ms(latencies, 95),
        p99_ms=percentile_ms(latencies, 99),
        decisions=dict(sorted(decisions.items())),
        unsafe_open_count=sum(sample.unsafe_open for sample in samples),
        audit_records=audit_records,
    )


def _print_result(result: ProfileResult) -> None:
    print(f"\n[{result.profile}]")
    print(f"offered_rate={result.offered_rate_eps:.1f} events/s")
    print(f"requests={result.requests}")
    print(f"errors={result.errors}")
    print(f"throughput={result.throughput_eps:.2f} events/s")
    print(
        "latency_ms="
        f"p50:{result.p50_ms:.3f} "
        f"p95:{result.p95_ms:.3f} "
        f"p99:{result.p99_ms:.3f}"
    )
    print(f"decisions={json.dumps(result.decisions, ensure_ascii=False)}")
    print(f"audit_records={result.audit_records}")
    print(f"unsafe_open_count={result.unsafe_open_count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Нагрузочный smoke-test decision/audit-контура PoC"
    )
    parser.add_argument(
        "--profile",
        choices=("baseline", "burst", "stress", "all"),
        default="all",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=6.0,
        help="Минимальная длительность профиля в секундах",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be > 0")
    if args.workers <= 0:
        parser.error("--workers must be > 0")

    print(
        "ВАЖНО: это smoke-test PoC decision/audit-контура. "
        "Он не подтверждает production p95 для реального CV/ML pipeline."
    )

    profiles = tuple(PROFILE_RATES) if args.profile == "all" else (args.profile,)
    results = [
        run_profile(profile, duration_s=args.duration, workers=args.workers)
        for profile in profiles
    ]

    if args.as_json:
        payload = [asdict(result) for result in results]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            _print_result(result)

    failed = any(
        result.errors > 0
        or result.unsafe_open_count > 0
        or result.audit_records != result.requests
        for result in results
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
