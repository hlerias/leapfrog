#!/usr/bin/env bash
# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
#
# Invoice Workflow demo — run entirely in-process with Hugging Face
# transformers (on your GPU/CPU). No Ollama, no server, no sudo. Weights
# download from Hugging Face and cache in ~/.cache/huggingface.
#
# This is the corporate-proof path: it works anywhere Hugging Face is reachable
# and Python can run, even when Ollama's download/registry hosts are blocked.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${HF_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"

printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
printf "  \033[1;96mLeapfrog Labs\033[0m \033[2m·\033[0m \033[1mInvoice Workflow — local (transformers)\033[0m\n"
printf "  \033[2m%s\033[0m\n" "The book is the why. This is where you build."
printf "  \033[2m%s\033[0m\n" "https://leapfrog.lerias.org"
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

# If torch + transformers are already importable (e.g. you ran the labs in this
# venv), reuse them. Otherwise install into a local .venv — a big first-time
# download, mostly torch.
if python -c "import torch, transformers" >/dev/null 2>&1; then
  say "Using the torch + transformers already in this environment"
else
  say "Setting up a Python env with torch + transformers"
  echo "    Heads up: this downloads PyTorch (~hundreds of MB). On an older"
  echo "    machine it can take 5+ minutes, and pip goes quiet while it unpacks"
  echo "    torch at the end — that's normal, not a freeze. Progress shown below."
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -r requirements-transformers.txt   # progress bars on (no -q)
fi

export LLM_BACKEND=transformers
export HF_MODEL="$MODEL"
say "Running the invoice workflow with local model '$MODEL' (first run downloads it)"
python invoice_workflow.py "$@"
