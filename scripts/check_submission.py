"""Generic submission sanity checker."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "AI_USAGE.md",
    "WORKLOG.md",
    "SELF_REVIEW.md",
    "docs/product.md",
    "docs/risks-and-ops.md",
    ".github/workflows/ci.yml",
]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"CAILA_API_KEY\s*=\s*[\"\']?(?!\.\.\.)[A-Za-z0-9_-]{16,}"),
]


def check_required_files() -> list[str]:
    return [path for path in REQUIRED if not (ROOT / path).exists()]


def check_secrets() -> list[str]:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.name == ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(str(path.relative_to(ROOT)))
                break
    return hits


def check_git_status() -> str | None:
    if not (ROOT / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "git status failed"
    return result.stdout.strip() or None


def main() -> int:
    failed = False
    missing = check_required_files()
    if missing:
        failed = True
        print("FAIL required files:", ", ".join(missing))
    else:
        print("OK   required files")

    secrets = check_secrets()
    if secrets:
        failed = True
        print("FAIL possible secrets:", ", ".join(secrets))
    else:
        print("OK   no obvious committed secrets")

    git_status = check_git_status()
    if git_status:
        print("WARN working tree is not clean")
    else:
        print("OK   git check (clean or not initialized)")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
