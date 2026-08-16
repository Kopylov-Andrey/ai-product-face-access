# Pre-flight before the timed task

Run this on the actual Windows/VS Code machine before exam day.

## 1. Local tooling

```powershell
python --version
git --version
claude --version
gh --version
python -m pip install -r requirements-dev.txt
python scripts/check_environment.py
python scripts/verify.py
```

Expected: Python/Git/pytest/Ruff are OK; Claude and `gh` should also be available if you plan to use them.

## 2. Claude Code

Open Claude Code from the repository root and run `/context`. Confirm that the root `CLAUDE.md` is listed. Ask Claude to make a harmless change in a temporary file, inspect the diff, then discard it.

## 3. CAILA (development/review only)

```powershell
python -m pip install -r requirements-llm.txt
$env:CAILA_API_KEY="<your key>"
$env:CAILA_MODEL="<exact model id>"
python tools/caila_preflight.py
```

Expected: authentication succeeds, the selected model responds, and latency is printed. Repeat for each candidate model you may use. Never put the key in a file committed to Git.

## 4. GitHub

Create a disposable private repository and push this starter. Confirm that GitHub Actions finishes green. Do this before the timed task so the real attempt only needs repository creation/push, not CI debugging.

## 5. Final exam-day rule

The final PoC should remain runnable without CAILA or any other external LLM API unless the actual task explicitly requires one. AI services are development/review tools, not a runtime dependency by default.
