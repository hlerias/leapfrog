# Leapfrog Labs

Runnable, vendor-neutral labs for **[Leapfrog](https://leapfrog.lerias.org)** — a free field guide to delivering AI on the cloud in a corporate environment, by Hugo Lerias.

The book is the *why* and the shape. These labs are where you build. Nine small, real examples — several run with **no API key at all**.

> 📘 **Read the book for free:** https://leapfrog.lerias.org
> 🧪 **Run the labs:** clone this repo and follow the quick start below.

## Made openly with AI

This project — the book and these labs — was written by pairing the author's experience with an AI model, openly. The book argues you should use AI in the open, and it was made that way. The ideas it rests on belong to the researchers it credits.

## Quick start

```bash
git clone https://github.com/hlerias/leapfrog.git
cd leapfrog
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Prefer one command with clear progress?** `./setup-labs.sh` does the venv +
install for you and tells you exactly what's happening (including the slow part):

```bash
./setup-labs.sh
```

> ⏳ **First install is slow — that's normal.** `requirements.txt` includes
> `sentence-transformers`, which pulls in **PyTorch** (a large download). On an
> older machine this can take **5+ minutes**, and pip often goes quiet during the
> final *"Installing collected packages: torch…"* step while it unpacks. It's not
> frozen — let it finish.
>
> **In a hurry?** Only the RAG labs (`02`, `06`, `09`) need the heavy install.
> For everything else, `pip install requests` is enough:
> ```bash
> pip install requests          # enough for labs 01, 03, 04, 05, 07, 08
> ```

Run one that needs no key at all:

```bash
python labs/08_trace.py         # no install needed at all
python labs/03_eval_gate.py     # no install needed at all
```

## No API key? Run models locally (free)

Several labs call a language model. You can use a paid provider, **or** run a small model locally with [Ollama](https://ollama.com) — perfect for locked-down environments:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=llama3.2
```

To use a hosted provider instead, copy `.env.example` to `.env`, fill it in, and `export` the values (or `set -a; source .env; set +a`).

## The labs

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

Each lab is short, commented, and independent. Start with `08_trace.py` or `03_eval_gate.py` (no key), then `02_naive_rag.py` / `06_rag_rerank.py` (local model, no key).

## Demos — putting it all together

Beyond the single-file labs, [`demos/`](demos/) has larger, runnable examples where the pieces come together into something you'd actually ship. Both run locally with no API key on the default path — even on a locked-down corporate machine.

- [**`demos/invoice-workflow/`**](demos/invoice-workflow/) — an Accounts-Payable triage pipeline: a local model reads a messy invoice into structure, then plain code validates the arithmetic, applies policy, and routes it. The model can be wrong; the pipeline catches it. Includes four hands-on, auto-graded exercises you extend yourself.
- [**`demos/ask-the-docs/`**](demos/ask-the-docs/) — grounded Q&A, the *anti-chatbot*: a human asks questions, the tool answers only from a fixed handbook, cites its source, and refuses when it can't find the answer instead of guessing.

See [`demos/README.md`](demos/README.md) for where to start.

## Setting up a lab machine

New to Linux, or on a locked-down Windows PC? Two step-by-step guides:
- [`docs/setup-virtualbox-ubuntu.md`](docs/setup-virtualbox-ubuntu.md) — a clean Ubuntu VM on Windows
- [`docs/setup-wsl.md`](docs/setup-wsl.md) — the lighter WSL route when VirtualBox is blocked

## License

- **Code** (`labs/`): [MIT](LICENSE) — use it freely.
- **Prose & docs**: [CC BY-NC-ND 4.0](LICENSE-CONTENT.md), matching the book.

## About

By **Hugo Lerias** — [LinkedIn](https://www.linkedin.com/in/hlerias). A personal project; the views are the author's own, not any employer's. Free to share. If it helps you ship something you'd been putting off, it did its job.

Issues and corrections welcome.
