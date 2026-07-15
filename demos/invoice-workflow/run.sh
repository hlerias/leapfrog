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

# 1. Python environment — reuse the repo root venv if present, else local ----
say "Setting up the Python environment"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -f "$REPO_ROOT/venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/venv/bin/activate"
  echo "    reusing repo venv at $REPO_ROOT/venv"
elif [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.venv/bin/activate"
  echo "    reusing repo venv at $REPO_ROOT/.venv"
else
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
fi
# ensure demo deps are present without hitting PyPI if already satisfied
python3 -c "import requests" 2>/dev/null || pip install -r requirements.txt

# 2. Pick a backend: Ollama if reachable, Hugging Face transformers otherwise -
# Both are local and free. Ollama is faster; transformers works where
# ollama.com is blocked (common on corporate networks).
export PATH="$HOME/.local/bin:$PATH"          # find a prior userspace install

_ollama_reachable() {
  curl -fsS --max-time 5 "https://ollama.com" >/dev/null 2>&1
}

_use_transformers() {
  say "ollama.com unreachable — switching to Hugging Face transformers backend (no server needed)"
  export LLM_BACKEND=transformers
  _HF_MODEL="${HF_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
  _HF_CACHE="$HOME/.cache/huggingface/hub"
  # only show the download warning if the model isn't cached yet
  if ! find "$_HF_CACHE" -name "*.safetensors" 2>/dev/null | grep -q .; then
    printf "\n\033[1;33m┌─ Heads up: downloading the model ────────────────────────────┐\033[0m\n"
    printf "\033[33m│\033[0m  '%s'\n" "$_HF_MODEL"
    printf "\033[33m│\033[0m  is a \033[1mbig download\033[0m (~500 MB – 1 GB). \033[1mFirst run only\033[0m —\n"
    printf "\033[33m│\033[0m  it can take several minutes on a slow connection.\n"
    printf "\033[33m│\033[0m  Every run after this reuses the cached model and is instant.\n"
    printf "\033[1;33m└──────────────────────────────────────────────────────────────┘\033[0m\n"
  else
    echo "    model: $_HF_MODEL (cached — will be instant)"
  fi
  say "Running the invoice workflow with transformers backend"
  python invoice_workflow.py "$@"
  exit $?
}

if command -v ollama >/dev/null 2>&1; then
  # already installed — skip the download entirely
  say "Ollama already installed — skipping download"
elif _ollama_reachable; then
  say "Ollama not found — installing it into \$HOME/.local (no sudo needed)"
  os="$(uname -s)"; arch="$(uname -m)"
  case "$arch" in x86_64|amd64) arch=amd64 ;; aarch64|arm64) arch=arm64 ;; esac
  if [ "$os" = "Linux" ]; then
    mkdir -p "$HOME/.local"
    curl -fsSL "https://ollama.com/download/ollama-linux-${arch}.tgz" -o /tmp/leapfrog-ollama.tgz
    tar -C "$HOME/.local" -xzf /tmp/leapfrog-ollama.tgz
    export PATH="$HOME/.local/bin:$PATH"
    echo "    installed to $HOME/.local/bin/ollama"
  elif [ "$os" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install ollama
    else
      echo "On macOS, install Ollama from https://ollama.com/download (or 'brew install ollama'), then re-run." >&2
      exit 1
    fi
  fi
else
  _use_transformers "$@"
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama install did not land on PATH — falling back to transformers." >&2
  _use_transformers "$@"
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
  printf "\n\033[1;33m┌─ Heads up: downloading the model ────────────────────────────┐\033[0m\n"
  printf "\033[33m│\033[0m  '%s' is a \033[1mbig download\033[0m (~1-2 GB). First run only —\n" "$MODEL"
  printf "\033[33m│\033[0m  it can take a few minutes on a slow connection. Progress below.\n"
  printf "\033[33m│\033[0m  Every run after this reuses it and is instant.\n"
  printf "\033[1;33m└──────────────────────────────────────────────────────────────┘\033[0m\n"
  say "Pulling the model '$MODEL'"
  ollama pull "$MODEL"
fi

# 5. Run the workflow against Ollama ----------------------------------------
export LLM_BASE_URL="${LLM_BASE_URL:-$OLLAMA_URL/v1}"
export LLM_API_KEY="${LLM_API_KEY:-ollama}"
export LLM_MODEL="$MODEL"
say "Running the invoice workflow with Ollama model '$MODEL'"
python invoice_workflow.py "$@"
