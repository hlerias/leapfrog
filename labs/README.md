# The Labs

Nine small, vendor-neutral examples from **[Leapfrog](https://leapfrog.lerias.org)**. Each lab is short, commented, and independent — read the code, then run it.

## Why do these?

The book makes the argument; the labs make it **undeniable**. Each one is built around a single **proof point** — one thing you watch happen on your own machine that proves the chapter's claim. Reading that naive RAG is fragile is easy to nod along to; watching it hand you the *wrong city* is what makes it stick. Every lab's header spells out, in plain language, what it is, how it works step by step, its proof point, and why it's worth your time. Do them roughly in order and you'll have *felt*, not just read, the whole arc: cost, retrieval, evals, structured output, tools, tracing, security, and shipping.

| File | What it shows | Chapter | Needs a key? |
|------|---------------|---------|--------------|
| `01_first_call.py` | Your first call — read the meter | 1 & 5 | needs a model (real key OR local Ollama) |
| `02_naive_rag.py` | Watch naive RAG fail | 7 | no API key (downloads a small local model) |
| `03_eval_gate.py` | A tiny eval gate | 8 & 9 | no API key (runs as-is) |
| `04_red_team_injection.py` | Red-team: indirect prompt injection | 11 | needs a model to compare replies |
| `05_structured_output.py` | Make it do one real thing — structured output | 6 | needs a model with JSON mode |
| `06_rag_rerank.py` | Fix the RAG — chunk, retrieve, rerank | 7 | no API key (downloads two small models) |
| `07_tool_use.py` | Give the model a tool | 6 | needs a model with tool calling |
| `08_trace.py` | Trace one request | 9 | no API key (runs as-is) |
| `09_ship_tiny.py` | Ship something tiny — end to end | Interlude | no API key (local + optional model) |

## The proof point — what each one shows you

- **01 · first call** — the `usage` block: output tokens cost far more than input, and that figure is real money.
- **02 · naive RAG** — ask for the *next* offsite and top-1 returns Berlin (Q2), not Lisbon (Q3).
- **03 · eval gate** — sabotage the prompt and the gate flips to `BLOCKED` under 0.90.
- **04 · injection** — the naive prompt prints `PWNED`; the defended one summarizes.
- **05 · structured output** — you get back `{sentiment, priority, tags}` you can branch on, self-corrected after a bad reply.
- **06 · rerank** — the same question now returns Lisbon (Q3) — the passage naive top-1 missed.
- **07 · tool use** — the model calls *your* function and composes the answer from what you returned.
- **08 · trace** — the whole request path as one JSON span, with a real `latency_ms`.
- **09 · ship tiny** — it grounds, structures, and refuses a disallowed route — the three ideas in ~50 lines.

## Start here (no key needed)

Four labs run with **no API key at all**:

- `08_trace.py` and `03_eval_gate.py` run as-is.
- `02_naive_rag.py`, `06_rag_rerank.py`, and `09_ship_tiny.py` download a small
  `sentence-transformers` model on first run (needs internet once), then run offline.

```bash
python labs/08_trace.py
python labs/03_eval_gate.py
```

## Run models locally (free, no key)

The model-based labs (`01`, `04`, `05`, `07`) call a language model. You can use a
hosted provider, **or** run a small model locally with [Ollama](https://ollama.com) —
ideal for locked-down environments:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=llama3.2
```

To use a hosted provider instead, copy `../.env.example` to `.env`, fill it in, and
`export` the values (or `set -a; source .env; set +a`).
