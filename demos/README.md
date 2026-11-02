# Demos

Bigger, runnable "putting it all together" examples that go beyond the single-file
[labs](../labs/). Each is self-contained, runs locally, and needs no API key for its
default path. They're where the book's ideas — grounding, structured output,
validation, containment — come together into something you'd actually ship.

| Demo | What it is | Needs a key? |
|------|------------|--------------|
| [`invoice-workflow/`](invoice-workflow/) | An Accounts-Payable triage pipeline: a **local model** reads a messy invoice into structure, then plain code validates the arithmetic, applies policy, and routes it. The model can be wrong; the pipeline catches it. Includes four hands-on, auto-graded exercises. | no (local model or `--offline`) |
| [`ask-the-docs/`](ask-the-docs/) | **Grounded Q&A — the anti-chatbot.** A human asks questions; the tool answers only from a fixed handbook, cites the source, and refuses when it can't find the answer instead of guessing. Extends the RAG labs. | no (retrieval-only; `--model` optional) |
| [`eval-harness/`](eval-harness/) | **How do you know it's working?** A pre-deployment eval gate for ask-the-docs: a golden set, scoring in layers (free checks first, an LLM judge last), the four signals from Chapter 7, and a per-metric gate that blocks a change the average would have shipped. Then it checks the judge against human labels. Includes four auto-graded exercises. | no (recorded responses; `--live` / `--judge` optional) |

## Which to start with

- **New to the whole picture?** [`invoice-workflow/`](invoice-workflow/) — run
  `python invoice_workflow.py --offline` to watch the four steps on canned data,
  then `./run_local.sh` for the real local model. Then try `your_turn.py` and
  extend the pipeline yourself.
- **Curious about human-in-the-loop without a chatbot?**
  [`ask-the-docs/`](ask-the-docs/) — run `python ask.py --demo` to see it answer
  from the handbook and *refuse* the one question that isn't in it.
- **Want to know if a change made it better or worse?**
  [`eval-harness/`](eval-harness/) — run `python3 eval_harness.py` to watch a
  "harmless" change get BLOCKED on one metric, then `--calibrate` to check the
  judge. No install at all.

All three run on a locked-down corporate machine (no admin, no API key) — that's the point.
