"""python -m sk_llm_eval.score --answers answers.jsonl --label "Model (chat UI)"

Scores pre-collected answers offline — useful for models reachable only through a
chat UI, or for re-scoring an earlier run after task checks change.

answers.jsonl: one {"id": "<task id>", "answer": "<model answer>"} per line.
Judge checks need --judge-model; otherwise they are skipped like in run.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .checks import run_check
from .judge import judge
from .run import slug, summarize
from .tasks import load_tasks, validate_tasks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score pre-collected answers")
    ap.add_argument("--answers", required=True, help="JSONL with {id, answer}")
    ap.add_argument("--label", required=True, help="display name in leaderboard")
    ap.add_argument("--tasks", default="tasks")
    ap.add_argument("--judge-model", default=os.environ.get("SK_EVAL_JUDGE_MODEL"))
    ap.add_argument("--judge-base-url", default=os.environ.get("SK_EVAL_JUDGE_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--judge-api-key", default=os.environ.get("SK_EVAL_JUDGE_API_KEY"))
    ap.add_argument("--out", default=None, help="default: results/<label>.json")
    args = ap.parse_args(argv)

    tasks = load_tasks(Path(args.tasks))
    errors = validate_tasks(tasks)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    by_id = {t["id"]: t for t in tasks}

    answers: dict[str, str] = {}
    with open(args.answers, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                d = json.loads(line)
                answers[d["id"]] = d["answer"]
    unknown = sorted(set(answers) - set(by_id))
    if unknown:
        print(f"unknown task ids: {unknown}", file=sys.stderr)
        return 1

    records = []
    for tid, task in sorted(by_id.items()):
        rec = {"id": tid, "category": task["category"], "prompt": task["prompt"]}
        if tid not in answers:
            rec.update(answer=None, passed=False, skipped=False, error="no answer", checks=[])
            records.append(rec)
            continue
        answer = answers[tid]
        rec["answer"] = answer
        results, passed = [], True
        for c in task["checks"]:
            if c["type"] == "judge":
                if not args.judge_model:
                    results.append({"type": "judge", "ok": None, "detail": "skipped: no --judge-model"})
                    continue
                ok, score, reason = judge(
                    task["prompt"], answer, c.get("rubric") or task.get("rubric"),
                    judge_model=args.judge_model, base_url=args.judge_base_url, api_key=args.judge_api_key,
                )
                results.append({"type": "judge", "ok": ok, "score": score, "detail": reason})
            else:
                ok, detail = run_check(c, answer)
                results.append({"type": c["type"], "ok": ok, "detail": detail})
            if ok is False:
                passed = False
        rec["skipped"] = all(r["ok"] is None for r in results)
        rec["passed"] = passed and not rec["skipped"]
        rec["checks"] = results
        records.append(rec)

    summary = summarize(records)
    out = {
        "model": args.label,
        "label": args.label,
        "base_url": None,
        "judge_model": args.judge_model,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "eval_version": __version__,
        "mode": "offline",
        "summary": summary,
        "records": records,
    }
    out_path = Path(args.out or f"results/{slug(args.label)}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in records:
        if not r.get("skipped") and not r["passed"]:
            fails = [c["detail"] for c in r["checks"] if c["ok"] is False] or [r.get("error")]
            print(f"✘ {r['id']}: {fails}")
    for cat, c in sorted(summary["categories"].items()):
        print(f"{cat:<12} {c['passed']:>3}/{c['total']:<3} {c['score']:>6}%")
    print(f"{'OVERALL':<12} {'':>7} {summary['overall']:>6}%")
    print(f"→ {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
