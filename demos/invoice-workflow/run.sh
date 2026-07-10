#!/usr/bin/env bash
# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
#
# Invoice Workflow demo — one command, everything configured.
# Clone the repo, run this, and it will: make a Python env, install Ollama if
# needed, pull a small local model, and run the invoice workflow end to end.
# No API key, no cost. Re-running is fast — each step is skipped if already done.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${LLM_MODEL:-llama3.2}"          # override: LLM_MODEL=llama3.2:1b ./run.sh
OLLAMA_URL="http://localhost:11434"

say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
printf "  \033[1;96mLeapfrog Labs\033[0m \033[2m·\033[0m \033[1mInvoice Workflow\033[0m\n"
printf "  \033[2m%s\033[0m\n" "The book is the why. This is where you build."
printf "  \033[2m%s\033[0m\n" "https://leapfrog.lerias.org"
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"

# 1. Python environment (isolated, self-contained) --------------------------
say "Setting up the Python environment"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 2. Ollama installed? ------------------------------------------------------
if ! command -v ollama >/dev/null 2>&1; then
  say "Ollama not found — installing it (from https://ollama.com; may ask for sudo)"
  curl -fsSL https://ollama.com/install.sh | sh
fi

# 3. Ollama running? --------------------------------------------------------
if ! curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  say "Starting the Ollama service"
  ollama serve >/tmp/leapfrog-ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1 && break
    sleep 1
  done
fi

# 4. Model pulled? ----------------------------------------------------------
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  say "Pulling the model '$MODEL' (first run only — this is the big download)"
  ollama pull "$MODEL"
fi

# 5. Run the workflow against a real local model ----------------------------
export LLM_BASE_URL="${LLM_BASE_URL:-$OLLAMA_URL/v1}"
export LLM_API_KEY="${LLM_API_KEY:-ollama}"
export LLM_MODEL="$MODEL"
say "Running the invoice workflow with local model '$MODEL'"
python invoice_workflow.py "$@"
