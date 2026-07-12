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
pip install -r requirements.txt          # shows progress; this one is small (just requests)

# 2. Ollama installed? (no sudo — installs into $HOME) ----------------------
# Corporate machines rarely grant sudo, so we install Ollama entirely in the
# user's home directory. Models live in ~/.ollama. Nothing touches the system.
export PATH="$HOME/.local/bin:$PATH"          # find a prior userspace install
if ! command -v ollama >/dev/null 2>&1; then
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
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama install did not land on PATH. Add it with:" >&2
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
  exit 1
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

# 5. Run the workflow against a real local model ----------------------------
export LLM_BASE_URL="${LLM_BASE_URL:-$OLLAMA_URL/v1}"
export LLM_API_KEY="${LLM_API_KEY:-ollama}"
export LLM_MODEL="$MODEL"
say "Running the invoice workflow with local model '$MODEL'"
python invoice_workflow.py "$@"
