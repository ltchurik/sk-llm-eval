"""Load and validate tasks from tasks/*.jsonl."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .checks import ALL_TYPES, DETERMINISTIC

REQUIRED = {"id", "category", "prompt", "checks"}
OPTIONAL = {"system", "notes", "source", "rubric", "volatile"}
ID_RE = re.compile(r"^[a-z_]+-\d{3,}$")


class TaskError(ValueError):
    pass


def load_tasks(tasks_dir: Path, category: str | None = None) -> list[dict]:
    tasks: list[dict] = []
    for path in sorted(tasks_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    task = json.loads(line)
                except json.JSONDecodeError as e:
                    raise TaskError(f"{path.name}:{lineno}: invalid JSON: {e}") from e
                task["_file"] = path.name
                task["_line"] = lineno
                tasks.append(task)
    if category:
        tasks = [t for t in tasks if t["category"] == category]
    return tasks


def validate_tasks(tasks: list[dict]) -> list[str]:
    """Return a list of errors (empty = OK)."""
    errors: list[str] = []
    seen: set[str] = set()
    for t in tasks:
        where = f"{t.get('_file')}:{t.get('_line')}"
        keys = set(t) - {"_file", "_line"}
        missing = REQUIRED - keys
        if missing:
            errors.append(f"{where}: missing {sorted(missing)}")
            continue
        extra = keys - REQUIRED - OPTIONAL
        if extra:
            errors.append(f"{where}: unknown fields {sorted(extra)}")
        if not ID_RE.match(t["id"]):
            errors.append(f"{where}: id {t['id']!r} must match {ID_RE.pattern}")
        if t["id"] in seen:
            errors.append(f"{where}: duplicate id {t['id']!r}")
        seen.add(t["id"])
        if t["category"] != t["_file"].removesuffix(".jsonl"):
            errors.append(f"{where}: category {t['category']!r} != file name")
        if not isinstance(t["checks"], list) or not t["checks"]:
            errors.append(f"{where}: checks must be a non-empty list")
            continue
        for c in t["checks"]:
            ct = c.get("type")
            if ct not in ALL_TYPES:
                errors.append(f"{where}: unknown check type {ct!r}")
                continue
            if ct in DETERMINISTIC and c.get("value") in (None, ""):
                errors.append(f"{where}: check {ct} needs 'value'")
            if ct in ("min_words", "max_words", "diacritics_ratio"):
                if not isinstance(c.get("value"), (int, float)) or isinstance(c.get("value"), bool):
                    errors.append(f"{where}: check {ct} needs a numeric 'value'")
            if ct in ("regex", "not_regex"):
                try:
                    re.compile(c.get("value", ""))
                except re.error as e:
                    errors.append(f"{where}: bad regex: {e}")
            if ct == "judge" and not (c.get("rubric") or t.get("rubric")):
                errors.append(f"{where}: judge check needs 'rubric'")
    return errors
