"""Minimal client for OpenAI-compatible /chat/completions. No dependencies."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


class ApiError(RuntimeError):
    pass


def chat(
    prompt: str,
    *,
    model: str,
    base_url: str,
    api_key: str | None = None,
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: int = 120,
    retries: int = 3,
) -> str:
    """Send one prompt, return the answer text. Retries with exponential backoff."""
    url = base_url.rstrip("/") + "/chat/completions"
    key = api_key or os.environ.get("SK_EVAL_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            last_err = ApiError(f"HTTP {e.code}: {msg}")
            if e.code in (400, 401, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            last_err = ApiError(str(e))
        time.sleep(2**attempt)
    raise last_err or ApiError("unknown error")
