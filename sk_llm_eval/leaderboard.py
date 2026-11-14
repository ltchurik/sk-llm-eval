"""python -m sk_llm_eval.leaderboard  — builds results/LEADERBOARD.md from results/*.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# display names for the category ids used in tasks/*.jsonl, in table order
CATEGORY_NAMES = {
    "gramatika": "Grammar",
    "register": "Register",
    "realie": "Facts",
    "format": "Formatting",
    "preklad": "Translation",
    "long_text": "Long text",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results/LEADERBOARD.md")
    args = ap.parse_args(argv)

    runs = []
    for p in sorted(Path(args.results).glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("summary", {}).get("overall") is None:
            continue
        runs.append(d)
    if not runs:
        print("no results", file=sys.stderr)
        return 1

    found = {c for r in runs for c in r["summary"]["categories"]}
    cats = [c for c in CATEGORY_NAMES if c in found] + sorted(found - set(CATEGORY_NAMES))
    runs.sort(key=lambda r: -r["summary"]["overall"])

    lines = ["# Leaderboard", "", "Score = % of tasks that passed all checks; Overall = mean of category scores. "
             "Tasks = number of scored tasks (judge tasks count only when a judge ran). Generated automatically.", ""]
    lines.append("| # | Model | Overall | " + " | ".join(CATEGORY_NAMES.get(c, c) for c in cats) + " | Tasks | Judge | Version | Date |")
    lines.append("|---|---|---|" + "---|" * len(cats) + "---|---|---|---|")
    for i, r in enumerate(runs, 1):
        s = r["summary"]
        cells = []
        for c in cats:
            v = s["categories"].get(c, {}).get("score")
            cells.append(f"{v:.1f}" if v is not None else "–")
        lines.append(
            f"| {i} | {r['label']} | **{s['overall']:.1f}** | "
            + " | ".join(cells)
            + f" | {sum(c['total'] for c in s['categories'].values())}"
            + f" | {r.get('judge_model') or '–'} | {r.get('eval_version', '–')} | {r['run_at'][:10]} |"
        )
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
