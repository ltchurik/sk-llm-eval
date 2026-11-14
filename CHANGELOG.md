# Changelog

Scores are comparable only within one task version. Every leaderboard row records the `eval_version` it was scored with.

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
