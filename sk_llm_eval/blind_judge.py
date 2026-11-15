"""Blind offline judging: anonymise answers for an external judge, then map verdicts back.

This is how the `judge` checks in results/ were graded (judge "Claude Opus (agent, blind)").

1. prepare — collect the answers of several models to every task with a `judge` check,
   shuffle them per task and label them A, B, C… The judge sees only the task, the rubric
   and the anonymous answer, never the model name.

       python -m sk_llm_eval.blind_judge prepare \\
           results/answers/qwen3.5-9b.jsonl results/answers/gemma3-12b.jsonl \\
           --out-dir judging/run1 --seed 1

   Writes judging/run1/judge_in.jsonl (what the judge reads), key.json (label → model,
   keep it away from the judge) and PROMPT.md (the judge instructions, filled in).

2. The judge (an LLM in a chat or agent session, or a human) reads judge_in.jsonl and writes
   judge_out.jsonl: one {"key": "<task>#<label>", "score": 0-10, "reason": "..."} per line.

3. merge — de-anonymise the verdicts into results/judge/<model>.<suffix>.jsonl. Verdicts
   for task ids already in the file are replaced; others are kept.

       python -m sk_llm_eval.blind_judge merge judging/run1

4. Re-score each model with those verdicts (score.py --judge-file … --meta-from …).

Mix answers of several models into one judging batch: the judge then compares answers to
the same task side by side, which keeps its scale consistent. To check the judge's
calibration, include models that already have verdicts as anchors and pass them to
`merge --anchors`: their old verdicts are kept and the pass/fail agreement is printed.
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
from pathlib import Path

from .judge import PASS_THRESHOLD
from .tasks import load_tasks

JUDGE_PROMPT = """\
You are a strict evaluator of Slovak language quality. Read the file {input} ({n} lines, \
JSON each with key, task, prompt, rubric, answer). Each line is one anonymous model answer \
to a Slovak-language task; the rubric (in Slovak) says what the answer must satisfy. \
Several answers to the same task are labelled A, B, C…; they come from different, unknown \
models. Do not try to guess which model wrote which. Judge each on its own merits against \
the rubric, but keep your scale consistent across answers to the same task.

Score each answer 0–10 ({threshold} = pass threshold: acceptable, natural Slovak meeting \
the rubric with at most minor slips). Be strict about grammar errors, missing diacritics, \
bohemisms, unnecessary anglicisms, wrong formal/informal address (vykanie/tykanie), factual \
errors, made-up facts, and ignoring instructions (length, form, language). An empty answer \
scores 0. An answer not in Slovak (e.g. Czech or Slovenian) scores at most 2. An answer \
that contains visible reasoning/thinking text or meta-commentary instead of just the \
requested output should be penalised accordingly.

Do not read any other files. Write the results to {output}, one JSON object per line: \
{{"key": "<key>", "score": <int>, "reason": "<one sentence in Slovak naming the concrete \
errors, quoting them where useful>"}}. All {n} keys must be present. Write valid UTF-8 JSON \
(ensure_ascii off). Reply only with "done N" where N is the number of lines written.
"""


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip() and not line.startswith("#")]


def _labels(n: int) -> list[str]:
    letters = string.ascii_uppercase
    return [letters[i] if i < 26 else letters[i // 26 - 1] + letters[i % 26] for i in range(n)]


def prepare(args: argparse.Namespace) -> int:
    tasks = [t for t in load_tasks(Path(args.tasks)) if any(c["type"] == "judge" for c in t["checks"])]
    if args.only:
        wanted = set(args.only)
        tasks = [t for t in tasks if t["id"] in wanted]

    answers: dict[str, dict[str, str]] = {}  # model -> id -> answer
    for p in map(Path, args.answers):
        model = p.name.removesuffix(".jsonl")
        if model in answers:
            print(f"duplicate model name {model!r}", file=sys.stderr)
            return 1
        answers[model] = {d["id"]: d.get("answer") or "" for d in _read_jsonl(p)}

    rng = random.Random(args.seed)
    lines, key = [], {}
    for t in tasks:
        rubric = next(c.get("rubric") for c in t["checks"] if c["type"] == "judge") or t.get("rubric")
        models = [m for m in answers if t["id"] in answers[m]]
        rng.shuffle(models)
        for label, m in zip(_labels(len(models)), models):
            k = f"{t['id']}#{label}"
            key[k] = m
            lines.append({"key": k, "task": t["id"], "prompt": t["prompt"], "rubric": rubric,
                          "answer": answers[m][t["id"]]})

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "judge_in.jsonl", "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    (out / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "PROMPT.md").write_text(
        JUDGE_PROMPT.format(input=(out / "judge_in.jsonl").resolve(), output=(out / "judge_out.jsonl").resolve(),
                            n=len(lines), threshold=PASS_THRESHOLD),
        encoding="utf-8",
    )
    print(f"{len(lines)} answers to {len(tasks)} tasks from {len(answers)} models → {out}/judge_in.jsonl")
    print(f"give the judge {out}/PROMPT.md; keep {out}/key.json away from it")
    return 0


def merge(args: argparse.Namespace) -> int:
    d = Path(args.dir)
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    verdicts = _read_jsonl(d / args.output)
    got = {v["key"] for v in verdicts}
    missing, unknown = sorted(set(key) - got), sorted(got - set(key))
    if missing or unknown:
        print(f"missing verdicts: {missing}\nunknown keys: {unknown}", file=sys.stderr)
        return 1

    per_model: dict[str, dict[str, dict]] = {}
    for v in verdicts:
        score = int(v["score"])
        if not 0 <= score <= 10:
            print(f"{v['key']}: score {score} out of range", file=sys.stderr)
            return 1
        tid = v["key"].rsplit("#", 1)[0]
        per_model.setdefault(key[v["key"]], {})[tid] = {"id": tid, "score": score, "reason": v.get("reason", "")}

    out_dir = Path(args.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    anchors = set(args.anchors or [])
    for model, new in sorted(per_model.items()):
        path = out_dir / f"{model}.{args.suffix}.jsonl"
        if model in anchors:
            old = {r["id"]: r["score"] for r in _read_jsonl(path)} if path.exists() else {}
            common = [t for t in new if t in old]
            agree = sum((new[t]["score"] >= PASS_THRESHOLD) == (old[t] >= PASS_THRESHOLD) for t in common)
            print(f"{model:<32} anchor: pass/fail agrees with {path} on {agree}/{len(common)} tasks (not written)")
            continue
        merged = {r["id"]: r for r in _read_jsonl(path)} if path.exists() else {}
        merged.update(new)
        with open(path, "w", encoding="utf-8") as f:
            for tid in sorted(merged):
                f.write(json.dumps(merged[tid], ensure_ascii=False) + "\n")
        passed = sum(r["score"] >= PASS_THRESHOLD for r in new.values())
        print(f"{model:<32} {len(new):>3} verdicts, {passed} pass → {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Blind offline judging of judge-check tasks")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="anonymise and shuffle answers for the judge")
    p.add_argument("answers", nargs="+", help="answers JSONL files; the file name (without .jsonl) is the model id")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--tasks", default="tasks")
    p.add_argument("--seed", type=int, default=None, help="shuffle seed (record it for reproducibility)")
    p.add_argument("--only", nargs="*", help="judge only these task ids")
    p.set_defaults(func=prepare)

    m = sub.add_parser("merge", help="map the judge's verdicts back to models")
    m.add_argument("dir", help="the --out-dir of prepare")
    m.add_argument("--output", default="judge_out.jsonl", help="verdicts file inside dir")
    m.add_argument("--results-dir", default="results/judge")
    m.add_argument("--suffix", default="opus-judge", help="file name: <model>.<suffix>.jsonl")
    m.add_argument("--anchors", nargs="*",
                   help="models that already have verdicts: report pass/fail agreement instead of overwriting")
    m.set_defaults(func=merge)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
