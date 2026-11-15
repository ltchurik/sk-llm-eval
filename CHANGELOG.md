# Changelog

Scores are comparable only within one task version. Every leaderboard row records the `eval_version` it was scored with.

## 0.2.2 — 2026-11-15

Tasks and checks are unchanged from 0.2.1, so 0.2.1 and 0.2.2 scores are directly comparable. All rows were re-scored with 0.2.2; no score changed.

### Documentation and tooling

- `docs/METHODOLOGY.md`: how every row was produced, with exact run commands, Ollama version, model digests, the Modelfiles of the thinking Qwen rows (`docs/modelfiles/`), how the Claude rows were collected, and the judge prompt, batches and calibration.
- `python -m sk_llm_eval.blind_judge prepare|merge`: the blind judging procedure (shuffle and anonymise answers per task, map verdicts back, compare anchors with `--anchors`) as a script instead of ad-hoc steps.
- `score --meta-from results/<model>.json` keeps the model, endpoint, run time, `run_settings` and latencies of an earlier API run when re-scoring with judge verdicts.

### Results

- Qwen 3.5 4B and 9B rerun with thinking on (32k context, 16384-token budget, Qwen's recommended thinking sampling: temperature 0.6, top_p 0.95, top_k 20, presence_penalty 1.5). Thinking lifts 9B from 52.9 to 63.0 and 4B from 39.9 to 44.8. The leaderboard now has 20 rows.
- Judge tasks for both rows graded blind by Claude Opus; the earlier no-thinking answers were mixed in as anchors and got the same pass/fail verdict in 45 of 46 cases.

## 0.2.1 — 2026-11-14

### Results

- 11 more open-weight models run locally through Ollama: Gemma 3 (4B, 12B), Gemma 4 (E4B, 12B, 26B-A4B), Qwen 3.5 (4B, 9B), Llama 3.2 3B, Phi-4 mini, Granite 4.1 8B and Mistral Nemo 12B. The leaderboard now has 18 rows.
- Judge tasks for the new rows were graded blind by Claude Opus, with answers shuffled and anonymised per task.
- Each Ollama row records its quantisation and thinking settings in `run_settings`.

### Fixes

- Checks loosened where a correct answer failed: `register-011` (any polite question with *vykanie*, not only one starting with *Prepáčte*), `preklad-004` (*Držím palce!*), `realie-046` (*žiaden*).
- All rows re-scored with these checks. No v0.2.0 score changed.

## 0.2.0 — 2026-11-14

### Tasks (138 → 207)

- New category **`preklad`** (14 tasks): EN→SK translation with idioms, false friends (*actual*, *eventually*, *sympathetic*), gender and case agreement.
- **`gramatika`** +27: rare genitive plurals (*piesní, kuchýň, jedál, mydiel, hier, nôh*), rhythmic-law exceptions (*čítajú, vtáčí*), instrumental plurals (*ľuďmi, deťmi, koňmi*), past tense *-li* in all plural genders, numbers written as one word, bohemisms (*zrovna, bysme*), capitalisation of street and square names.
- **`format`** +8: postal codes, academic titles, *a. s.*, *a pod.*, dates in running text, ISO currency codes, the multiplication sign.
- **`register`** +4: plural participle in *vykanie* (*Boli ste*, not *Bola ste*), formal address of a woman with a title.
- **`realie`** +11, including one hallucination trap.
- **`long_text`** +5: a harder diacritics restoration, consistent *vykanie* over a whole text, no anglicisms, dates and money inside prose.
- Every new deterministic task was checked against a correct answer and a typical wrong answer before it was added.

### Fixes

- `gramatika-029` was wrong: it asked to "fix" *Dvaja psi sa hrali na dvore*, which is already correct (*dvaja psi* and *dva psy* are both standard). It now asks to fix *Dvaja psy*, and both correct forms pass.

- Checks loosened where a correct answer failed: `register-017` (*Ďakujem, že si prišiel* without *ti*), `register-019` (the blank alone, *sadnite*), `format-038` (*2 × 3 metre*), `gramatika-064` (*presne*, *akurát* as well as *práve*), `preklad-002`, `preklad-013`.
- Markdown emphasis (`**zo**`) no longer breaks regex checks.

### Runner

- `--resume` and `--answers-out`: answers are written as they arrive, so long local runs survive interruptions.
- `--extra-body` merges JSON into the request (e.g. `{"reasoning_effort": "none"}`), plus a `--timeout` option.
- `<think>…</think>` blocks are stripped from answers.
- The leaderboard shows the number of scored tasks and the task version for each row.

### Results

- First non-Claude rows: three open-weight models run locally through Ollama.
- All Claude rows re-scored on the 207 tasks. The new judge tasks and all judge tasks of the Ollama rows were graded blind by Claude Opus (answers shuffled and anonymised per task).

## 0.1.0 — 2026-11-09

First release: 138 tasks in 5 categories, runner, LLM judge, offline scoring, leaderboard, CI.
