"""Single cross-platform verification entry point used locally and in CI."""

from __future__ import annotations

import subprocess
import sys


def run(label: str, cmd: list[str]) -> bool:
    print(f"\n== {label} ==")
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def main() -> int:
    commands = [
        ("lint", [sys.executable, "-m", "ruff", "check", "."]),
        ("tests", [sys.executable, "-m", "pytest", "-q"]),
        ("happy demo", [sys.executable, "-m", "app.demo", "--scenario", "happy"]),
        ("risky demo", [sys.executable, "-m", "app.demo", "--scenario", "risky"]),
        ("submission check", [sys.executable, "scripts/check_submission.py"]),
    ]
    ok = all(run(label, cmd) for label, cmd in commands)
    print("\nREADY" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
