"""python -m sk_llm_eval.run --model gpt-4o --base-url https://api.openai.com/v1

Runs every task against an OpenAI-compatible endpoint and writes
results/<model>.json. Judge tasks require --judge-model (same endpoint, or another
one via --judge-base-url).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .api import ApiError, chat
from .checks import run_check
from .judge import judge
from .tasks import load_tasks, validate_tasks

DEFAULT_SYSTEM = "Odpovedaj po slovensky, stručne a presne."


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", s.lower()).strip("-")


def eval_task(task: dict, args: argparse.Namespace) -> dict:
    rec = {"id": task["id"], "category": task["category"], "prompt": task["prompt"]}
    t0 = time.time()
    try:
        answer = chat(
            task["prompt"],
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            system=task.get("system", DEFAULT_SYSTEM),
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except ApiError as e:
        rec.update(answer=None, passed=False, error=str(e), checks=[], latency=time.time() - t0)
        return rec
    rec["latency"] = round(time.time() - t0, 2)
    rec["answer"] = answer

    results = []
    passed = True
    for c in task["checks"]:
        if c["type"] == "judge":
            if not args.judge_model:
                results.append({"type": "judge", "ok": None, "detail": "skipped: no --judge-model"})
                continue
            rubric = c.get("rubric") or task.get("rubric")
            ok, score, reason = judge(
                task["prompt"],
                answer,
                rubric,
                judge_model=args.judge_model,
                base_url=args.judge_base_url or args.base_url,
                api_key=args.judge_api_key or args.api_key,
            )
            results.append({"type": "judge", "ok": ok, "score": score, "detail": reason})
        else:
            ok, detail = run_check(c, answer)
            results.append({"type": c["type"], "ok": ok, "detail": detail})
        if ok is False:
            passed = False
    # a task whose only checks were skipped judges does not count
    rec["skipped"] = all(r["ok"] is None for r in results)
    rec["passed"] = passed and not rec["skipped"]
    rec["checks"] = results
    return rec


def summarize(records: list[dict]) -> dict:
    by_cat: dict[str, dict] = {}
    for r in records:
        if r.get("skipped"):
            continue
        c = by_cat.setdefault(r["category"], {"passed": 0, "total": 0})
        c["total"] += 1
        c["passed"] += int(r["passed"])
    for c in by_cat.values():
        c["score"] = round(100 * c["passed"] / c["total"], 1) if c["total"] else None
    scored = [c["score"] for c in by_cat.values() if c["score"] is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else None
    return {"overall": overall, "categories": by_cat}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run sk-llm-eval")
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default=os.environ.get("SK_EVAL_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--api-key", default=None, help="default: $SK_EVAL_API_KEY or $OPENAI_API_KEY")
    ap.add_argument("--judge-model", default=os.environ.get("SK_EVAL_JUDGE_MODEL"))
    ap.add_argument("--judge-base-url", default=os.environ.get("SK_EVAL_JUDGE_BASE_URL"))
    ap.add_argument("--judge-api-key", default=os.environ.get("SK_EVAL_JUDGE_API_KEY"))
    ap.add_argument("--tasks", default="tasks")
    ap.add_argument("--category", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--out", default=None, help="default: results/<model>.json")
    ap.add_argument("--label", default=None, help="display name in leaderboard (default: model)")
    args = ap.parse_args(argv)

    tasks = load_tasks(Path(args.tasks), args.category)
    errors = validate_tasks(tasks)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        print("no tasks", file=sys.stderr)
        return 1

    print(f"model={args.model} tasks={len(tasks)} judge={args.judge_model or '-'}")
    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(eval_task, t, args): t for t in tasks}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            records.append(r)
            mark = "·" if r.get("skipped") else ("✔" if r["passed"] else "✘")
            print(f"[{i:>3}/{len(tasks)}] {mark} {r['id']}" + (f"  ({r['error'][:60]})" if r.get("error") else ""))

    records.sort(key=lambda r: r["id"])
    summary = summarize(records)
    out = {
        "model": args.model,
        "label": args.label or args.model,
        "base_url": args.base_url,
        "judge_model": args.judge_model,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "eval_version": __version__,
        "summary": summary,
        "records": records,
    }
    out_path = Path(args.out or f"results/{slug(args.model)}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    for cat, c in sorted(summary["categories"].items()):
        print(f"{cat:<12} {c['passed']:>3}/{c['total']:<3} {c['score']:>6}%")
    print(f"{'OVERALL':<12} {'':>7} {summary['overall']:>6}%")
    print(f"→ {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
