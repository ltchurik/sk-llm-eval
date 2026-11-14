"""Deterministic answer checks.

Each task has a list of `checks`; the task passes only if all of them pass.

Types:
  contains      – answer contains the string (case-insensitive, whitespace-normalized)
  not_contains  – answer does NOT contain the string (case-insensitive)
  exact         – normalized answer == value
  regex         – re.search(pattern, answer)   (case-sensitive; flag "i" = ignorecase)
  not_regex     – re.search finds no match
  min_words     – answer has at least N words
  max_words     – answer has at most N words
  diacritics_ratio – share of words containing a Slovak diacritic letter >= value
                     (real Slovak prose sits around 0.35–0.55; text with stripped
                     diacritics scores ~0)
  judge         – LLM-as-judge against a rubric (handled by judge.py)
"""

from __future__ import annotations

import re
import unicodedata

DETERMINISTIC = {"contains", "not_contains", "exact", "regex", "not_regex", "min_words", "max_words", "diacritics_ratio"}
ALL_TYPES = DETERMINISTIC | {"judge"}

SK_DIACRITICS = "áäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ"
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def diacritics_ratio(text: str) -> float:
    ws = words(text)
    if not ws:
        return 0.0
    return sum(any(ch in SK_DIACRITICS for ch in w) for w in ws) / len(ws)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?<!\w)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\w)", r"\1", text)  # *italic*
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
    if t == "min_words":
        n = len(words(ans))
        return n >= int(val), f"min_words {val} (got {n})"
    if t == "max_words":
        n = len(words(ans))
        return n <= int(val), f"max_words {val} (got {n})"
    if t == "diacritics_ratio":
        r = diacritics_ratio(ans)
        return r >= float(val), f"diacritics_ratio >= {val} (got {r:.2f})"
    if t == "judge":
        raise ValueError("judge check must be handled by judge.py")
    raise ValueError(f"unknown check type: {t}")
