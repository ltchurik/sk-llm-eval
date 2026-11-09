# sk-llm-eval

**A practical benchmark for Slovak language quality in LLM responses.**

[![validate](https://github.com/ltchurik/sk-llm-eval/actions/workflows/validate.yml/badge.svg)](https://github.com/ltchurik/sk-llm-eval/actions/workflows/validate.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24091954.svg)](https://doi.org/10.5281/zenodo.24091954)

Academic Slovak benchmarks (skLEP, Trojsten) measure NLU and problem solving. This one measures what users and companies actually care about when picking a model: **does it write correct Slovak?**

| Category | What it measures |
|---|---|
| `gramatika` | declension, i/y spelling, diacritics, rhythmic law, prepositions |
| `register` | formal *vykanie* vs. informal *tykanie*, salutations, standard vs. colloquial style |
| `realie` | Slovak facts without hallucination (institutions, law, geography) |
| `format` | dates, numbers, currency, phone numbers, quotation marks, abbreviations per Slovak orthography |
| `long_text` | 100–300-word outputs: consistent diacritics, no anglicisms, correct register held over a whole text, restoring stripped diacritics |

Zero dependencies (Python 3.10+ standard library only). Works with any OpenAI-compatible API: OpenAI, Anthropic (via proxy), Google, Mistral, OpenRouter, Ollama, vLLM, LM Studio…

## Quick start

```bash
git clone https://github.com/ltchurik/sk-llm-eval && cd sk-llm-eval

# validate task files
python -m sk_llm_eval.validate

# OpenAI
export OPENAI_API_KEY=sk-...
python -m sk_llm_eval.run --model gpt-4o --judge-model gpt-4o

# OpenRouter (one key, every model)
export SK_EVAL_API_KEY=sk-or-...
python -m sk_llm_eval.run --base-url https://openrouter.ai/api/v1 \
  --model anthropic/claude-sonnet-4.5 --judge-model openai/gpt-4o

# local model via Ollama
python -m sk_llm_eval.run --base-url http://localhost:11434/v1 --model qwen2.5:7b

# build the leaderboard from results/*.json
python -m sk_llm_eval.leaderboard
```

Without `--judge-model`, `judge` tasks are skipped and excluded from the score; deterministic tasks always run.

### Offline scoring (chat-only models)

Collect answers by hand into a JSONL (`{"id": "...", "answer": "..."}` per line) and score them without an API:

```bash
python -m sk_llm_eval.score --answers results/answers/my-model.jsonl --label "My Model (chat)"
```

The answer files are committed under `results/answers/` so every leaderboard row is reproducible.

## How scoring works

Every task has a list of `checks`. A task **passes only if all checks pass**. Category score = % of tasks passed. Overall = mean of category scores.

```jsonc
{
  "id": "gramatika-011",
  "category": "gramatika",
  "prompt": "Ktorý tvar je správny: „krásný“ alebo „krásny“? Odpovedz len správnym slovom.",
  "checks": [
    {"type": "regex", "value": "\\bkrásny\\b", "flags": "i"},
    {"type": "not_regex", "value": "\\bkrásný\\b", "flags": "i"}
  ]
}
```

| Type | Meaning |
|---|---|
| `contains` / `not_contains` | case-insensitive substring |
| `exact` | normalized answer equals value |
| `regex` / `not_regex` | `re.search`; `"flags": "i"` = ignorecase |
| `min_words` / `max_words` | word-count bounds |
| `diacritics_ratio` | share of words containing a Slovak diacritic ≥ value (catches stripped diacritics in long text) |
| `judge` | LLM-as-judge against a `rubric`, score 0–10, pass at ≥ 7 |

Answers are normalized (NFC, nbsp → space, collapsed whitespace) before checking.

Prompts and rubrics are in Slovak on purpose: the benchmark tests how a model behaves for a Slovak user.

## Results

See [`results/LEADERBOARD.md`](results/LEADERBOARD.md). Each run writes `results/<model>.json` with full answers, so you can see *why* a model failed.

How the current rows were produced (read before drawing conclusions):

- **`(agent)` rows** — the model ran as a Claude Code subagent that read the prompts file and wrote answers; it was told not to read the task checks. Not a clean API run (the agent harness adds its own system prompt), but it is the real model.
- **`(chat)` row** — answers typed by the model inside a chat session; same caveat.
- **Judge** — `judge` tasks were graded by Claude Opus as a blind subagent: it saw four anonymous answer sets without model names. It is still a Claude model grading Claude models, so expect some family bias. Verdicts are in `results/judge/`.
- The author of the tasks also wrote the Fable answers. Treat that row as a task sanity check, not a measurement.

Independent API runs of other model families are the most useful thing to contribute right now.

## Contributing

New tasks are the most valuable contribution. Rules:

1. One task = one JSONL line in `tasks/<category>.jsonl`.
2. `id` is `<category>-NNN`; continue the numbering.
3. Prefer deterministic checks; use `judge` only where a regex cannot verify the answer.
4. For facts, add `"source"` (URL). For things that change (rates, office holders), add `"volatile": true`.
5. Run `python -m sk_llm_eval.validate` — CI enforces it on every PR.

Ideas for new categories: `preklad` (EN→SK without anglicisms), `agent` (tool calling in Slovak), `long_text` (diacritics consistency over 500+ words).

## Citing

See [CITATION.cff](CITATION.cff) (GitHub's "Cite this repository" button renders it). The DOI [10.5281/zenodo.24091954](https://doi.org/10.5281/zenodo.24091954) covers all versions.

## License

MIT. All tasks are original, not derived from other datasets.
