"""Minimal client for OpenAI-compatible /chat/completions. No dependencies."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request


class ApiError(RuntimeError):
    pass


_THINK_RE = re.compile(r"<think>.*?(</think>|$)", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Drop <think>…</think> blocks that some reasoning models put into the answer."""
    return _THINK_RE.sub("", text).strip()


def chat(
    prompt: str,
    *,
    model: str,
    base_url: str,
    api_key: str | None = None,
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: int = 300,
    retries: int = 3,
    extra_body: dict | None = None,
) -> str:
    """Send one prompt, return the answer text. Retries with exponential backoff."""
    url = base_url.rstrip("/") + "/chat/completions"
    key = api_key or os.environ.get("SK_EVAL_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    payload.update(extra_body or {})
    body = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    last_err: Exception | None = None
    attempt = rate_limited = 0
    while attempt < retries:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return strip_reasoning(data["choices"][0]["message"]["content"] or "")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            last_err = ApiError(f"HTTP {e.code}: {msg}")
            if e.code in (400, 401, 403, 404):
                break
            if e.code == 429 and rate_limited < RATE_LIMIT_RETRIES:
                # rate limits (e.g. 20 requests/min) need a longer wait than other errors,
                # and waiting for them should not use up the normal retries
                rate_limited += 1
                time.sleep(_retry_after(e) or min(60, 10 * rate_limited))
                continue
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            last_err = ApiError(str(e))
        time.sleep(2**attempt)
        attempt += 1
    raise last_err or ApiError("unknown error")


RATE_LIMIT_RETRIES = 8


def _retry_after(e: urllib.error.HTTPError) -> float | None:
    """Seconds to wait from a Retry-After header, capped at two minutes."""
    try:
        return min(120.0, max(1.0, float(e.headers.get("Retry-After", ""))))
    except (TypeError, ValueError):
        return None
