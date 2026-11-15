# Methodology and reproducing the results

This document records how every leaderboard row of v0.2.1 was produced, so that each row can be re-run or checked. The README has the short version; this is the full one.

## What is in the repository

| Path | Content |
|---|---|
| `tasks/*.jsonl` | the 207 tasks with their checks (v0.2.1) |
| `results/<model>.json` | per-task results: answer, every check and its outcome, latency, and `run_settings` (sampling, token budget, quantisation, hardware) |
| `results/answers/<model>.jsonl` | raw answers, one `{id, answer}` per line, exactly as the model returned them (reasoning blocks stripped) |
| `results/judge/<model>.opus-judge.jsonl` | the judge's verdict on each judge task: `{id, score, reason}` |
| `docs/modelfiles/` | Ollama Modelfiles for the thinking Qwen rows |
| `sk_llm_eval/blind_judge.py` | the anonymise → judge → de-anonymise procedure used for all verdicts |

Any row can be re-scored from its answers and verdicts without calling a model:

```bash
python -m sk_llm_eval.score --answers results/answers/qwen3.5-9b.jsonl \
  --label "Qwen 3.5 9B (Ollama, no thinking)" \
  --judge-file results/judge/qwen3.5-9b.opus-judge.jsonl --judge-label "Claude Opus (agent, blind)" \
  --meta-from results/qwen3.5-9b.json --out results/qwen3.5-9b.json
python -m sk_llm_eval.leaderboard
```

This reproduces the committed `results/*.json` exactly (apart from `eval_version` when the code version changes).

## Prompting

- Every task is sent as one user message. The system message is `Odpovedaj po slovensky, stručne a presne.` (`DEFAULT_SYSTEM` in `sk_llm_eval/run.py`) unless the task sets its own `system`.
- One attempt per task. No retries, no few-shot examples, no answer extraction beyond the normalisation described in the README (`<think>…</think>` blocks are removed before checking).
- An empty answer, a request error or a timeout counts as a failed task.

## Open-weight models (`(Ollama)` rows)

**Environment**

| | |
|---|---|
| Machine | NVIDIA DGX Spark (GB10, 128 GB unified memory), driver 580.178.04 |
| Server | Ollama 0.40.5, OpenAI-compatible endpoint `http://localhost:11434/v1` |
| Runs | 2026-11-14 (non-thinking rows), 2026-11-14/15 (thinking rows) |
| Concurrency | one model loaded at a time; `--workers` 2–4 parallel requests (affects speed only) |

**Models.** Tags are as published in the Ollama library at the time of the run. Tags can be re-pointed later; the ID (manifest digest prefix from `ollama list`) identifies the exact weights.

| Row | Ollama tag | ID | Quantisation |
|---|---|---|---|
| Gemma 3 4B | `gemma3:4b` | `68ceab7e468a` | Q4_K_M |
| Gemma 3 12B | `gemma3:12b` | `b92b218582c5` | Q4_K_M |
| Gemma 4 E4B | `gemma4:e4b` | `dc35e8d9c606` | Q4_K_M |
| Gemma 4 12B | `gemma4:12b` | `6114515d63c1` | Q4_K_M |
| Gemma 4 26B-A4B | `gemma4:26b-a4b` | `001e5dafc3c7` | Q4_K_M |
| Granite 4.1 8B | `granite4.1:8b` | `444af1c4b2fe` | Q4_K_M |
| Laguna XS 2.1 Q8 | `laguna-xs-2.1:q8_0` | `a249c0765c04` | Q8_0 |
| Llama 3.2 3B | `llama3.2:3b` | `a80c4f17acd5` | Q4_K_M |
| Mistral Nemo 12B | `mistral-nemo:12b` | `e7e06d107c6c` | Q4_0 |
| Ornith 1.5 35B | `ornith-1.5:35b` | `9f3b89b25219` | Q4_K_M |
| Phi-4 mini 3.8B | `phi4-mini:3.8b` | `78fad5d182a7` | Q4_K_M |
| Qwen 3.5 4B (no thinking) | `qwen3.5:4b` | `d8b0f5e9760c` | Q4_K_M |
| Qwen 3.5 9B (no thinking) | `qwen3.5:9b` | `56671c2ab938` | Q4_K_M |
| Qwen 3.5 4B (thinking) | `qwen3.5:4b-32k` (from `qwen3.5:4b`) | `d87a749b91cc` | Q4_K_M |
| Qwen 3.5 9B (thinking) | `qwen3.5:9b-32k` (from `qwen3.5:9b`) | `a008daebf808` | Q4_K_M |
| Qwen 3.8 27B Q8 (no thinking) | `qwen3.8:27b-mtp-q8_0` | `8a1582877303` | Q8_0 |

**Settings.** There are three groups. `run_settings` in each `results/<model>.json` repeats them per row.

1. **Default.** Models that think by default kept thinking on. Temperature 0, 8192-token budget, Ollama's default context.

   ```bash
   python -m sk_llm_eval.run --base-url http://localhost:11434/v1 --model gemma3:12b \
     --label "Gemma 3 12B (Ollama)" --max-tokens 8192 --timeout 900 --workers 4 --resume
   ```

2. **Qwen, no thinking.** Thinking off, because with thinking Qwen 3.5 4B managed about 7 tasks in 30 minutes and the dense Qwen 3.8 27B generates only about 5 tokens/s on this machine.

   ```bash
   python -m sk_llm_eval.run --base-url http://localhost:11434/v1 --model qwen3.5:9b \
     --label "Qwen 3.5 9B (Ollama, no thinking)" \
     --extra-body '{"reasoning_effort": "none"}' --max-tokens 1500 --timeout 900 --workers 4 --resume
   ```

3. **Qwen, thinking.** Thinking on, 32k context, 16384-token budget and Qwen's recommended sampling for thinking mode (temperature 0.6, top_p 0.95, top_k 20, presence_penalty 1.5). At temperature 0 the thinking looped until it hit the budget. With Ollama's default 8192-token context the thinking was cut off, which gave empty answers. Top_p and top_k come from the Modelfile, because the runner does not send them.

   ```bash
   ollama create qwen3.5:9b-32k -f docs/modelfiles/qwen3.5-9b-32k.Modelfile
   python -m sk_llm_eval.run --base-url http://localhost:11434/v1 --model qwen3.5:9b-32k \
     --label "Qwen 3.5 9B (Ollama, thinking)" \
     --temperature 0.6 --extra-body '{"presence_penalty": 1.5}' --max-tokens 16384 --timeout 1800 \
     --workers 4 --resume --out results/qwen3.5-9b-thinking.json \
     --answers-out results/answers/qwen3.5-9b-thinking.jsonl
   ```

   These runs took about 5 minutes per task. The 4B took about 8 hours and the 9B about 5.5 hours for all 207 tasks. Because sampling is not greedy, a re-run gives slightly different answers. Expect a difference of a few points, not an identical score.

The runs above leave judge tasks unscored (no `--judge-model`). They were then graded as described under [Judge](#judge).

## API models through OpenRouter (`(OpenRouter)` rows)

GPT-6.1 Sol, Gemini 4 Argon, Grok 4.7, DeepSeek V4 Pro, Mistral Large 4 and Llama 4 Maverick were run on 2026-11-15 through [OpenRouter](https://openrouter.ai)'s OpenAI-compatible API, with OpenRouter's default provider routing. The exact model id is in `model` of each result file.

```bash
export SK_EVAL_API_KEY=...   # OpenRouter key
python -m sk_llm_eval.run --base-url https://openrouter.ai/api/v1 --model openai/gpt-6.1-sol \
  --label "GPT-6.1 Sol (OpenRouter)" --max-tokens 8192 --timeout 600 --workers 3 --resume
```

- Temperature 0 and an 8192-token budget. Reasoning was left at each provider's default (no `reasoning` parameter sent), so models that reason by default did so. Providers that do not accept a temperature ignore it.
- New OpenRouter accounts are limited to 20 requests per minute per model. The client waits on HTTP 429 (honouring `Retry-After`) and a second `--resume` pass retried anything that still failed. In the end no task had an API error.
- The full runs of all six models cost about $1.70 in total (plus about $0.20 for a 23-task pilot).
- Mistral Large 4 returned an empty answer on 3 short grammar tasks (`gramatika-011`, `-015`, `-029`). A later single request for `gramatika-011` returned an answer after about 2,300 reasoning tokens, so the empty answers look transient. They still count as failures, because every row gets one attempt per task.

## Claude rows

These rows were not produced through an API, and they are not directly comparable with the Ollama rows.

- **`(agent)` rows: Opus, Sonnet, Haiku.** Each model ran as a Claude Code subagent (`general-purpose`, model set to `opus`, `sonnet` or `haiku`). The subagent got a file of `{id, prompt}` pairs and these instructions: answer every prompt in Slovak following the system instruction `Odpovedaj po slovensky, stručne a presne.`, answer exactly as asked, do not read any other file (in particular not the repository, tasks or checks), and do not use web search or tools to look up answers. It wrote `{id, answer}` lines, which were scored with `sk_llm_eval.score`. The harness adds its own system prompt, and the sampling settings are those of Claude Code, which are not recorded.
- **`(chat)` row: Fable.** The task author answered the 138 v0.1.0 tasks with this model in a chat session, while writing the tasks. The 69 tasks added in v0.2.0 were answered by the same model as a subagent, under the instructions above. Because the author saw the checks, treat this row as a sanity check that the tasks can be solved, not as a measurement.

## Judge

23 tasks have a `judge` check: 12 in `register`, 9 in `long_text` and 2 in `realie`. An LLM grades the answer 0–10 against the task's Slovak rubric, and the task passes at 7 or more.

The online judge in `sk_llm_eval/judge.py` (`--judge-model`) was **not** used for the leaderboard. All verdicts come from **Claude Opus running as a Claude Code subagent** in a blind procedure, implemented in `sk_llm_eval/blind_judge.py`:

1. **Anonymise.** For each judge task, the answers of all models in the batch are shuffled and labelled A, B, C… The judge gets a file with `key` (`<task>#<label>`), `task`, `prompt`, `rubric` and `answer`. The label-to-model key stays outside the judge's reach.
2. **Grade.** The judge is told to read only that file and grade each answer against the rubric on a consistent scale across answers to the same task. It is strict about grammar errors, missing diacritics, bohemisms, unnecessary anglicisms, wrong *vykanie/tykanie*, factual errors, made-up facts and ignored instructions (length, form, language). An empty answer scores 0, an answer in Czech or Slovenian at most 2, and visible thinking or meta-commentary is penalised. It writes `{key, score, reason}` with a one-sentence reason in Slovak. `blind_judge prepare` writes the full prompt into `PROMPT.md`.
3. **De-anonymise.** `blind_judge merge` maps the verdicts back into `results/judge/<model>.opus-judge.jsonl`.
4. **Re-score** each row with `score --judge-file … --meta-from …` (see the top of this document).

**Current verdicts (v0.2.3): one round for all rows.** All 598 judge answers (23 tasks × 26 rows) were graded again in one round, so every row is graded on the same scale. The tasks were split into six batches of 3–4 tasks. Each batch held the answers of all 26 rows to its tasks, shuffled per task, so the judge saw every answer to a task side by side. Each batch went to a separate Claude Opus subagent with the prompt that `blind_judge prepare` writes to `PROMPT.md`. Among other things, it tells the judge to grade one task at a time and not to mark an answer down because others to the same task are better, or up because they are worse.

```bash
python -m sk_llm_eval.blind_judge prepare results/answers/*.jsonl --out-dir judging/all-1 --seed 101 \
  --only long_text-001 long_text-008 register-002 register-012
# … batches all-2 to all-6 with seeds 102–106, the next tasks in sorted order (every 6th judge task)
```

`register-009` was then graded again on its own (seed 107), after its rubric was corrected to accept lowercase *vaša/vám* (see CHANGELOG 0.2.3).

**Why the re-grading.** When the six OpenRouter rows were first graded together with two already-graded rows as anchors, pass/fail agreed with the earlier verdicts on only 34 of 46 anchor answers, and every change went from pass to fail. Next to very strong answers, the judge became stricter with mid-level ones. Grading all rows in one round removes that drift between rows. Compared with the earlier verdicts, the single round agrees on pass/fail for 561 of 598 answers (94 %), with changes in both directions (16 fail → pass, 21 pass → fail). For the rows that existed before, overall scores moved by at most 1.3 points, and the order of the leaderboard barely changed.

**Earlier batches (v0.1.0–v0.2.2, now replaced).** Before v0.2.3 the verdicts came from separate batches: the v0.1.0 tasks of the Claude rows were graded per model while the tasks were built; Qwen 3.8 27B, Ornith and Laguna in one batch (77 answers); the other 11 non-thinking Ollama rows in two sessions (253 answers); and the thinking Qwen rows with the non-thinking Qwen rows as anchors (92 answers, pass/fail agreement with the anchors 45 of 46). The instructions grew a little between those batches; the prompt in `blind_judge.py` is the union of their rules.

**Known limits of the judge**

- A Claude model grades Claude models, so expect some family bias in the Claude rows. Claude Opus is both a graded row and the judge.
- The judge is an agent session, not a fixed API call at temperature 0. Repeating it will not give identical scores. Agreement between two rounds was 94 % on pass/fail.
- Give each judge its own output path and keep helper scripts out of shared folders: in the v0.2.3 round, two parallel judge sessions shared a helper script, and one batch's verdicts were written to the wrong file. It was caught because the keys of each output must match its own input (`merge` checks this), and the batch was written again.

## Checking the deterministic checks

After each new row, the failed tasks were read by hand to look for checks that failed a correct answer (Markdown, synonyms, valid alternative forms). Every such fix was tested against a correct answer and a typical wrong one, the version was bumped, and all rows were re-scored. The changes are listed in [CHANGELOG.md](../CHANGELOG.md). Scores are comparable only within one task version.

## Adding a row

1. Run the model with `sk_llm_eval.run` (or collect answers elsewhere and use `sk_llm_eval.score`). Write the settings that `run.py` does not record (quantisation, hardware, context size) into `run_settings` of the result file.
2. Grade its judge tasks blind together with a few already-graded rows as anchors:
   ```bash
   python -m sk_llm_eval.blind_judge prepare results/answers/new-model.jsonl \
     results/answers/qwen3.5-9b.jsonl results/answers/gemma3-12b.jsonl --out-dir judging/new --seed 1
   # give judging/new/PROMPT.md to the judge, which writes judging/new/judge_out.jsonl
   python -m sk_llm_eval.blind_judge merge judging/new --anchors qwen3.5-9b gemma3-12b
   ```
3. If pass/fail on the anchors agrees poorly with their earlier verdicts (well below ~90 %), the judge's scale has drifted. Grade all rows again in one round, as in v0.2.3, instead of merging the new verdicts.
4. Re-score with `score --judge-file … --meta-from …` and rebuild the leaderboard (`python -m sk_llm_eval.leaderboard`).
