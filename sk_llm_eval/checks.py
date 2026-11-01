"""Deterministic answer checks.

Each task has a list of `checks`; the task passes only if all of them pass.

Types:
  contains      – answer contains the string (case-insensitive, whitespace-normalized)
  not_contains  – answer does NOT contain the string (case-insensitive)
  exact         – normalized answer == value
  regex         – re.search(pattern, answer)   (case-sensitive; flag "i" = ignorecase)
  not_regex     – re.search finds no match
  judge         – LLM-as-judge against a rubric (handled by judge.py)
"""

from __future__ import annotations

import re
import unicodedata

DETERMINISTIC = {"contains", "not_contains", "exact", "regex", "not_regex"}
ALL_TYPES = DETERMINISTIC | {"judge"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _flags(check: dict) -> int:
    return re.IGNORECASE if "i" in check.get("flags", "") else 0


def run_check(check: dict, answer: str) -> tuple[bool, str]:
    """Return (passed, detail)."""
    t = check["type"]
    ans = normalize(answer)
    val = check.get("value", "")

    if t == "contains":
        ok = normalize(val).casefold() in ans.casefold()
        return ok, f"contains {val!r}"
    if t == "not_contains":
        ok = normalize(val).casefold() not in ans.casefold()
        return ok, f"not_contains {val!r}"
    if t == "exact":
        ok = ans.casefold().rstrip(".") == normalize(val).casefold().rstrip(".")
        return ok, f"exact {val!r}"
    if t == "regex":
        ok = re.search(val, ans, _flags(check)) is not None
        return ok, f"regex /{val}/"
    if t == "not_regex":
        ok = re.search(val, ans, _flags(check)) is None
        return ok, f"not_regex /{val}/"
    if t == "judge":
        raise ValueError("judge check must be handled by judge.py")
    raise ValueError(f"unknown check type: {t}")
