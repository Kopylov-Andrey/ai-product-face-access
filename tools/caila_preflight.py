"""CAILA development-time preflight using the OpenAI-compatible SDK.

Usage (PowerShell):
  $env:CAILA_API_KEY = (Get-Clipboard).Trim()
  $env:CAILA_MODEL='...'
  python -m pip install -r requirements-llm.txt
  python tools/caila_preflight.py

The API key is intentionally read only from the environment.
"""

from __future__ import annotations

import os
import time


def main() -> int:
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "FAIL install optional dependency: "
            "python -m pip install -r requirements-llm.txt"
        )
        return 2

    api_key = (os.getenv("CAILA_API_KEY") or "").strip()
    model = (os.getenv("CAILA_MODEL") or "").strip()
    base_url = (
        os.getenv(
            "CAILA_BASE_URL",
            "https://caila.io/api/adapters/openai",
        )
        or ""
    ).strip().rstrip("/")

    if not api_key:
        print("FAIL CAILA_API_KEY is not set")
        return 2

    if not model:
        print("FAIL CAILA_MODEL is not set")
        return 2

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0,
        max_retries=1,
    )

    print(f"base_url={base_url}")
    print(f"model={model}")

    try:
        started = time.perf_counter()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly CAILA_OK and nothing else.",
                }
            ],
        )

        latency = time.perf_counter() - started

        if not response.choices:
            print("FAIL provider returned no choices")
            return 1

        message = response.choices[0].message
        content = (message.content or "").strip()

        print(f"latency={latency:.2f}s")
        print(f"finish_reason={response.choices[0].finish_reason}")
        print(f"response={content!r}")

        if content == "CAILA_OK":
            print("OK   deterministic content check")
        elif "CAILA_OK" in content:
            print("WARN model added extra text, but endpoint is healthy")
        elif content:
            print("WARN endpoint worked, but content check differed")
        else:
            print("WARN endpoint worked, but visible content is empty")

        print("OK   authentication + model + chat completion")
        return 0

    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {type(exc).__name__}: {exc}")

        cause = exc.__cause__
        level = 0

        while cause is not None and level < 5:
            print(
                f"CAUSE[{level}] "
                f"{type(cause).__name__}: {cause!r}"
            )
            cause = cause.__cause__
            level += 1

        return 1


if __name__ == "__main__":
    raise SystemExit(main())