# Project instructions for Claude Code

This repository is a generic starter for a time-boxed AI Product system-design task.
It MUST remain domain-neutral until the real task is received.

## Priorities
1. System/product reasoning is more important than code volume.
2. Build only the smallest vertical PoC that proves a chosen architectural idea.
3. Prefer deterministic, dependency-light code.
4. Risky/uncertain paths must fail safe; never invent unsafe automatic actions.
5. Every meaningful behavior added to the PoC must be covered by a test.
6. Do not invent requirements, measurements, legal claims, or production guarantees.
7. Keep assumptions explicit in documentation.
8. Keep WORKLOG factual and consistent with actual Git history.
9. Keep AI_USAGE factual: record useful AI mistakes and rejected suggestions as they happen.
10. Never write API keys, tokens, credentials, employee data, or biometric data into the repo.

## Language
Все пользовательские и сдаваемые Markdown-документы пишутся на русском языке.
Английский допускается только для кода, идентификаторов, названий файлов,
стандартных сокращений и терминов, перевод которых ухудшает техническую точность.

## Before proposing a commit
Run:

    python scripts/verify.py

Review the diff and keep the commit limited to one coherent stage of work.

## Scope discipline
Do not add Kubernetes, databases, web UI, cloud deployment, external APIs, or ML training unless the actual task makes them necessary to prove the selected scenario.
