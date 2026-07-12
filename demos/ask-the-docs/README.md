# Ask the handbook — grounded Q&A, *not* a chatbot

The book warns against open-ended chatbots that confidently answer anything (and
bluff when they don't know). This is the deliberate opposite, and it's the
natural extension of the RAG labs ([02](../../labs/02_naive_rag.py) +
[06](../../labs/06_rag_rerank.py)): a human asks a question and the tool answers
**only** from a fixed set of documents — with three guardrails from the chapters.

```
 you ask  →  retrieve + rerank (lab 06)  →  confident enough?
                                             ├─ no  → "not in the handbook"  (refuse, no guess)
                                             └─ yes → answer, grounded in the passage, with the source cited
```

- **Grounded** — every answer comes from a retrieved passage, and it's **cited**.
- **Bounded** — below a confidence threshold it says *"I couldn't find that in the
  handbook"* and **won't guess**. That's containment (lab 09).
- **One job** — it answers questions about *this handbook*, not "anything".

That's what "AI with guardrails" feels like next to a chatbot that bluffs.

## Run it

**Fresh machine:**
```bash
cd demos/ask-the-docs
./setup.sh
```
Installs the retrieval stack (same as lab 06 — a large first-time PyTorch
download, so it warns you), then runs the sample questions.

**Already have Python + sentence-transformers:**
```bash
pip install -r requirements.txt
python ask.py --demo          # a few sample questions, incl. one it should refuse
python ask.py --ask "Where is the next offsite?"
python ask.py                 # interactive: ask your own questions
```

First run downloads two small retrieval models (~180 MB); after that it's fast.
No API key needed.

## What to watch

The sample run asks five questions. Four are answered from the handbook, cited to
the file they came from. The fifth — *"What is the company's policy on remote
work?"* — **isn't in the docs**, so the tool refuses instead of inventing an
answer. That refusal is the whole point: a chatbot would make something up.

## Let a local model phrase the answer (optional)

By default the answer **is** the cited passage. Add `--model` (or set `LLM_API_KEY`)
and a local model phrases the answer using **only** that passage — grounded
generation, still cited, still able to refuse:

```bash
# with a local Ollama, for example:
export LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama LLM_MODEL=llama3.2
python ask.py --demo --model
```

The model is told: *answer using only this text; if it doesn't answer, say so.*
So even the phrased version can't wander off the source.

## The handbook

Plain-text policies in [`handbook/`](handbook/) — travel, expenses, on-call,
offsites (the same world as the labs). Drop in your own `.txt` files and ask
about them; the source filename becomes the citation.

## Files

| File | What it is |
|------|------------|
| `ask.py` | The grounded-Q&A tool: retrieve → rerank → refuse-or-answer, cited |
| `handbook/` | The documents it answers from (one topic per `.txt`) |
| `setup.sh` | One-command setup + sample run |
| `test_ask.py` | Tests the decision logic (refuse / answer / cite) with no models |
| `requirements.txt` | `sentence-transformers` (+ `requests` for the optional model path) |

## Tuning

| Env var | Default | Meaning |
|---------|---------|---------|
| `ASK_THRESHOLD` | `0.0` | cross-encoder score below which it refuses (raise to be stricter) |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | Ollama defaults | the optional model that phrases answers |
