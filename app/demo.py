"""Infrastructure-only demo.

This is deliberately domain-neutral. Replace it after receiving the real task.
It exists only to prove that local execution and CI work before the timed task.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DemoResult:
    scenario: str
    decision: str
    side_effect_allowed: bool
    reason: str


def run_demo(scenario: str) -> DemoResult:
    if scenario == "happy":
        return DemoResult(
            scenario=scenario,
            decision="allow",
            side_effect_allowed=True,
            reason="generic happy-path placeholder",
        )
    if scenario == "risky":
        return DemoResult(
            scenario=scenario,
            decision="manual_review",
            side_effect_allowed=False,
            reason="generic fail-safe placeholder",
        )
    raise ValueError(f"Unsupported scenario: {scenario}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=("happy", "risky"), required=True)
    args = parser.parse_args()
    print(json.dumps(asdict(run_demo(args.scenario)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
