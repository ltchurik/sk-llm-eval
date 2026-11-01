"""LLM-as-judge for free-form answers (register, style, hallucination…).

The judge receives the prompt, the model's answer and a rubric, and returns a 0–10 score.
A task passes at score >= PASS_THRESHOLD.
"""

from __future__ import annotations

import re

from .api import chat

PASS_THRESHOLD = 7

JUDGE_SYSTEM = (
    "You are a strict evaluator of Slovak language quality. You grade a language model's "
    "answer against the given rubric. Reply ONLY in this format:\n"
    "SCORE: <integer 0-10>\n"
    "REASON: <one sentence>"
)

JUDGE_TEMPLATE = """TASK GIVEN TO THE MODEL:
{prompt}

MODEL ANSWER:
{answer}

RUBRIC (what the answer must satisfy; written in Slovak):
{rubric}

Grade the answer 0–10. 10 = fully satisfies the rubric, 0 = fails completely.
Grammar errors, missing diacritics, or wrong formal/informal address (vykanie/tykanie) \
must lower the score substantially."""


def judge(
    prompt: str,
    answer: str,
    rubric: str,
    *,
    judge_model: str,
    base_url: str,
    api_key: str | None = None,
) -> tuple[bool, int, str]:
    """Return (passed, score, reason)."""
    text = chat(
        JUDGE_TEMPLATE.format(prompt=prompt, answer=answer, rubric=rubric),
        model=judge_model,
        base_url=base_url,
        api_key=api_key,
        system=JUDGE_SYSTEM,
        temperature=0.0,
        max_tokens=200,
    )
    m = re.search(r"SCORE:\s*(\d+)", text, re.IGNORECASE)
    score = int(m.group(1)) if m else 0
    score = max(0, min(10, score))
    r = re.search(r"REASON:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    reason = r.group(1).strip() if r else text.strip()[:200]
    return score >= PASS_THRESHOLD, score, reason
