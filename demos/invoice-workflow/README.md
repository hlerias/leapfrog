# Invoice Workflow — putting it all together

> **Status: internal / not yet linked from the main site.** A self-contained
> "capstone" demo: one command clones-and-runs a real Accounts-Payable triage
> workflow where a **local** language model does the reading and plain code does
> everything that has to be correct.

The book's throughline in one runnable example. A model is good at *one* thing
here — reading a messy, human-formatted invoice and turning it into structure.
It is not trusted with anything else. The arithmetic, the policy, and the
routing are ordinary code the model never touches:

```
 raw invoice text
      │
      ▼
 1. EXTRACT     local LLM  ->  structured JSON      (the model's one job)
 2. VALIDATE    JSON parses & fits the schema       (retry once if not)
 3. RECONCILE   do the numbers actually add up?     (code, not the model)
 4. DECIDE      a bounded policy picks the route     (containment)
      │
      ▼
 auto-approve · needs-approval · hold-review
```

If the model hallucinates a total, step 3 catches it. If it invents a route,
step 4 refuses it. The model can be wrong and the workflow still holds.

## Run it (one command, everything configured)

**Fresh machine?** `setup.sh` installs *everything* — system tools (python3,
venv, pip, curl, git), Ollama, a local model, and the Python deps — then runs
the demo:

```bash
cd demos/invoice-workflow
./setup.sh
```

Works on Linux (apt / dnf / pacman / zypper) and macOS (Homebrew). On Windows,
run it inside WSL — see [`../../docs/setup-wsl.md`](../../docs/setup-wsl.md).

**Already have Python + curl?** Skip straight to the runner:

```bash
cd demos/invoice-workflow
./run.sh
```

`run.sh` is self-configuring: it creates a Python venv, installs **[Ollama](https://ollama.com)**
if it isn't already there, pulls a small model (`llama3.2` by default), and runs
the workflow against the four sample invoices. No API key, no cost. First run
downloads the model; after that it's instant.

Low on RAM? Use a smaller model:

```bash
LLM_MODEL=llama3.2:1b ./run.sh
```

Already have a model server (Ollama, vLLM, LM Studio, a hosted provider)? Skip
`run.sh` and point the workflow straight at it:

```bash
pip install -r requirements.txt
export LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama LLM_MODEL=llama3.2
python invoice_workflow.py
```

## See the pipeline with no model at all

Every step except the extraction is deterministic. To watch steps 2–4 run with
zero network — using canned "correct extractions" in `fixtures/` — pass
`--offline`:

```bash
python invoice_workflow.py --offline
```

Expected result: `acme` **auto-approves**, `globex` **needs approval** (over the
€1,000 threshold), and `initech` (its printed total doesn't add up) and
`umbrella` (missing total and invoice number) are both **held for review**.

## What's here

| File | What it is |
|------|------------|
| `setup.sh` | Fresh-machine installer: system tools, then hands off to `run.sh` |
| `run.sh` | One-command bootstrap: env + Ollama + model + run |
| `invoice_workflow.py` | The four-step pipeline, ~180 lines, commented |
| `sample_invoices/` | Four realistic messy invoices, covering all three routes |
| `fixtures/` | Canned correct extractions, for `--offline` and the tests |
| `test_pipeline.py` | Golden routes + a mock-model contract test (no network) |

## Tests

```bash
python test_pipeline.py
```

Two checks, both offline:
- **Golden** — the pipeline routes every sample invoice as expected.
- **Contract** — the real `extract_via_llm` HTTP path is driven against a mock
  OpenAI-compatible server: a good reply parses, a malformed reply triggers the
  retry, and persistent garbage raises so the invoice is held. This exercises
  the exact code that talks to Ollama, minus the model itself.

## Tuning

| Env var | Default | Meaning |
|---------|---------|---------|
| `LLM_MODEL` | `llama3.2` | model tag to pull and use |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | any OpenAI-compatible endpoint |
| `LLM_API_KEY` | `ollama` | key (Ollama ignores it) |
| `APPROVAL_THRESHOLD` | `1000` | amount above which an invoice needs approval |
