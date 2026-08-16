"""Cross-platform local environment preflight."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = {
    "git": ["git", "--version"],
    "pytest": [sys.executable, "-m", "pytest", "--version"],
    "ruff": [sys.executable, "-m", "ruff", "--version"],
    "claude": ["claude", "--version"],
    "gh": ["gh", "--version"],
}

OPTIONAL = {"claude", "gh"}


def first_line(cmd: list[str]) -> tuple[bool, str]:
    executable = cmd[0]

    if executable == sys.executable:
        resolved = executable
    else:
        resolved = shutil.which(executable)
        if resolved is None:
            return False, "not found"

    run_cmd = [resolved, *cmd[1:]]

    # On Windows, command-line tools installed through npm/native shims can
    # resolve to .cmd/.bat files. Execute those through cmd.exe rather than
    # passing the shim directly to CreateProcess.
    if os.name == "nt" and Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        command_line = subprocess.list2cmdline(run_cmd)
        run_cmd = [comspec, "/d", "/s", "/c", command_line]

    try:
        result = subprocess.run(run_cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return False, f"found at {resolved}, but could not execute: {exc}"

    text = (result.stdout or result.stderr).strip().splitlines()
    detail = text[0] if text else f"exit={result.returncode}"
    return result.returncode == 0, detail


def main() -> int:
    print(f"python: {sys.version.split()[0]} ({sys.executable})")
    required_ok = True
    for name, cmd in TOOLS.items():
        ok, detail = first_line(cmd)
        level = "OK" if ok else ("WARN" if name in OPTIONAL else "FAIL")
        print(f"{level:4} {name:7} {detail}")
        if not ok and name not in OPTIONAL:
            required_ok = False
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
