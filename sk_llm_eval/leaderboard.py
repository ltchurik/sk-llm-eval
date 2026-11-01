"""python -m sk_llm_eval.leaderboard  — builds results/LEADERBOARD.md from results/*.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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

    cats = sorted({c for r in runs for c in r["summary"]["categories"]})
    runs.sort(key=lambda r: -r["summary"]["overall"])

    lines = ["# Leaderboard", "", "Score = % of tasks that passed all checks. Generated automatically.", ""]
    lines.append("| # | Model | Overall | " + " | ".join(cats) + " | Judge | Date |")
    lines.append("|---|---|---|" + "---|" * len(cats) + "---|---|")
    for i, r in enumerate(runs, 1):
        s = r["summary"]
        cells = []
        for c in cats:
            v = s["categories"].get(c, {}).get("score")
            cells.append(f"{v:.1f}" if v is not None else "–")
        lines.append(
            f"| {i} | {r['label']} | **{s['overall']:.1f}** | "
            + " | ".join(cells)
            + f" | {r.get('judge_model') or '–'} | {r['run_at'][:10]} |"
        )
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
