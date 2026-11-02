# Eval harness — how do you know it's working?

A teammate proposes a "harmless" change to [`ask-the-docs`](../ask-the-docs/):
lower the refusal threshold so it answers more questions. More questions get
answered. Is it better?

You can't settle that with `assert output == expected`, because open text
comes out differently every time. Chapter 8 says what to do instead:
*evaluations replace unit tests*. You run the change against a golden set and
gate the deployment on the result. This demo is that gate, in code, with the
two things most teams skip: scoring **each metric on its own**, and **checking
the judge**.

```
 golden set ─► run v1 + v2 ─► score in layers ─► compare per metric ─► SHIP / BLOCKED
                                (cheap first)                          + check the judge
```

It covers the first of Chapter 9's three places evaluation lives: the
**pre-deployment gate**, which catches a regression before a single user
meets it.

## Run it

No install, no network, no API key. A fresh `python3` is enough:

```bash
cd demos/eval-harness
python3 eval_harness.py                 # v2 vs v1, all five steps → BLOCKED (exit code 1)
python3 eval_harness.py --version v1    # v1 alone → SHIP (exit code 0)
python3 eval_harness.py --calibrate     # check the judge against human labels
python3 eval_harness.py --brief         # just the scores and the verdict
python3 test_harness.py                 # the tests → ALL TESTS PASSED
```

Or `./setup.sh`, which runs the tests and then the harness.

The exit code is `0` for SHIP and `1` for BLOCKED, so the harness works as a
CI check as it stands.

## What it does, step by step

**① Golden set.** [`golden.jsonl`](golden.jsonl) has 18 questions about the
ask-the-docs handbook. Each says which file should be cited, which facts a
right answer must contain, and whether the system should refuse. Sixteen are
answerable. Two are not in the handbook, so the right answer is an honest
refusal: *"What is the company's policy on remote work?"* (the same question
`ask.py --demo` refuses) and one about vacation days.

**② Run two versions.** v1 is what runs today (refusal threshold `0.0`). v2
is the proposed change (threshold `-2.0`). Each response records the **whole
response path** (Chapter 8), not just the answer: the passages retrieved, with
scores, the answer, the cited source, and whether it refused.

**③ Score in layers**, cheap and free first, the judge last (Chapter 8's
layered gates: fail fast and cheap, spend the expensive gate only on what
passed the free one):

| Layer | What it checks | Cost |
|-------|----------------|------|
| L1 programmatic | refused exactly when it should? cited a source? the expected file? | free |
| L2 grounded | is every key fact in the passage it used **and** in the answer? | free |
| L3 judge | a model scores the answer against [`rubric.md`](rubric.md), only if L1 and L2 passed | tokens |

Then it reports Chapter 7's four signals for each version:

| Signal | Chapter 7's question | Measured here as |
|--------|----------------------|------------------|
| retrieval recall | did you fetch the right chunks at all? | the right passage is among those retrieved (16 answerable questions) |
| context relevance | was what you fetched actually on point? | the passage the answer was built from is the right one (16 answerable) |
| faithfulness | did the answer stick to the retrieved context, or wander off and invent? | L2 passed (all 18). A refusal claims nothing, so it counts as faithful; an answer to a question it should refuse does not |
| correctness | was the final answer, all things considered, actually right? | L1, L2 and L3 all passed (16 answerable) |

**④ Compare & gate.** A table of the four signals, v1 vs v2, with the change
in points. A metric blocks the change if it is below its minimum **or** fell
by more than the tolerance. The harness prints `SHIP` or `BLOCKED`, naming
the metric and the cases that caused it.

**⑤ Check the judge** (`--calibrate`). Chapter 9: a model judging a model has
blind spots of its own, so you align your judge against human ratings on a
sample before you trust it. The harness compares the judge's verdicts on v2
with the human labels in [`humans.jsonl`](humans.jsonl), prints the agreement,
and lists every disagreement.

## What to watch

v2 answers two more questions than v1, and its **correctness goes up**, from
75% to 81%. On a dashboard that counts answered questions, v2 looks better.
But one of the two new answers is to the remote-work question, with an
invented policy. **Faithfulness falls from 94% to 89%**, the same numbers as
Chapter 9's example of a regression the gate should catch:

```
BLOCKED — faithfulness 94% → 89% (case q17: answered a question it should refuse)
```

Look at the line above it: a gate on the **average** of the four signals would
have shipped v2 (90.8% → 91.0%). The gain in one metric hides the loss in
another. That's why this gate checks each metric on its own.

Then run `--calibrate`. The judge agrees with the humans on 16 of 18 cases.
One disagreement is a **fluent but wrong** answer about premium economy that
the judge passed and a person failed. The other is a short, right answer the
judge failed. The harness's correctness number leans on that judge. In the
book's words: *a judge you haven't checked against people is not a
measurement; it's a guess with a decimal point.*

## Your turn — four auto-graded exercises

Each one runs with plain `python3`, grades your code against its own small
golden set, prints PASS/FAIL per case with hints that reveal a little more
each time, and then shows your code change a real decision.

| Exercise | You write | Passing makes... |
|----------|-----------|------------------|
| [`your_turn_1.py`](your_turn_1.py) | the citation check (layer 1) | a mis-cited answer flip from PASS to FAIL |
| [`your_turn_2.py`](your_turn_2.py) | the faithfulness check (layer 2) | the gate catch the remote-work answer |
| [`your_turn_3.py`](your_turn_3.py) | the regression gate, per metric | the gate block v2, where the average-only stub ships it |
| [`your_turn_4.py`](your_turn_4.py) | a new golden case from a production failure | the gate catch a v3 that only fails on that case |

Exercise 4 is Chapter 9's feedback loop: production traces go to people, they
label real failures, and those failures go back into the golden set.
Stuck? [`solutions/`](solutions/), but try first.

## The data is synthetic

Everything in `responses/`, `judge/` and `humans.jsonl` is **synthetic, for
this demo**: made up to show the harness, not recorded from a real run. The
golden questions are real, though. Every fact they check is in
[`../ask-the-docs/handbook/`](../ask-the-docs/handbook/), and a test makes
sure of it. The harness reads the handbook in place; it never copies it.

## Optional: run it for real

```bash
./setup.sh --live                    # installs sentence-transformers (large PyTorch download)
python eval_harness.py --live        # runs the real ask-the-docs retrieval for v1 and v2
python eval_harness.py --live --judge   # ...and a local model as the judge
python eval_harness.py --nli         # adds an entailment model to layer 2
```

- `--live` imports [`../ask-the-docs/ask.py`](../ask-the-docs/ask.py) and
  produces the same response records. With `LLM_API_KEY` set, a local model
  phrases the answers, like `ask.py --model`. Your numbers will differ from
  the recorded ones; the recorded data is shaped to show the proof point.
  The recorded judge verdicts only match the recorded responses, so a live
  run skips layer 3 unless you add `--judge`.
- `--judge` sends each case that passed layers 1 and 2 to a local model with
  [`rubric.md`](rubric.md) as its instructions. With `--calibrate` it judges
  all 18 and compares with the humans.
- `--nli` adds semantic entailment to layer 2: does the passage support the
  answer? This is the second of the three kinds of check in Chapter 9. It
  uses a small entailment model (`cross-encoder/nli-deberta-v3-small`, a
  one-time download). Watch what it does: it catches the fluent-but-wrong
  premium-economy answer that the string check and the judge both passed,
  and it also flags some right answers, such as "wine" for "alcohol". A
  scorer is only as trustworthy as your check of it against people.

## Files

| File | What it is |
|------|------------|
| `eval_harness.py` | The harness: layers, the four signals, the per-metric gate, calibration |
| `golden.jsonl` | 18 golden questions about the ask-the-docs handbook |
| `responses/v1.jsonl`, `responses/v2.jsonl` | Recorded response paths for each version (synthetic) |
| `judge/v1.jsonl`, `judge/v2.jsonl` | Recorded judge verdicts (synthetic) |
| `humans.jsonl` | Human labels for v2, to check the judge (synthetic) |
| `rubric.md` | What the judge is told to check |
| `test_harness.py` | Tests: golden set vs handbook, each layer, the numbers, both gates, exit codes, the exercises |
| `your_turn_1.py` … `your_turn_4.py` | Auto-graded exercises |
| `solutions/README.md` | Solutions and the why (try first) |
| `setup.sh` | Runs the tests and the harness; `--live` installs the optional extras |

## Tuning

| Env var | Default | Meaning |
|---------|---------|---------|
| `EVAL_MIN_RECALL` | `0.85` | minimum retrieval recall |
| `EVAL_MIN_RELEVANCE` | `0.80` | minimum context relevance |
| `EVAL_MIN_FAITHFULNESS` | `0.90` | minimum faithfulness |
| `EVAL_MIN_CORRECTNESS` | `0.70` | minimum correctness |
| `EVAL_TOLERANCE` | `0.02` | how far a metric may fall vs the baseline (0.02 = 2 points) |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | Ollama defaults | the optional judge (`--judge`) and answer phrasing (`--live`) |
