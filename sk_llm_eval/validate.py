"""python -m sk_llm_eval.validate  — validates tasks/*.jsonl, exit 1 on error."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .tasks import load_tasks, validate_tasks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate task files")
    ap.add_argument("--tasks", default="tasks", help="directory with *.jsonl")
    args = ap.parse_args(argv)

    tasks = load_tasks(Path(args.tasks))
    errors = validate_tasks(tasks)
    counts = Counter(t["category"] for t in tasks)
    for cat, n in sorted(counts.items()):
        print(f"{cat:<12} {n:>4} tasks")
    print(f"{'total':<12} {len(tasks):>4} tasks")
    if errors:
        print(f"\n{len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
