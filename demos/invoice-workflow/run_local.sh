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
  printf "\n\033[1;33m┌─ Heads up: this next step takes a while ─────────────────────┐\033[0m\n"
  printf "\033[33m│\033[0m  The local model runs on \033[1mPyTorch\033[0m, a big download (hundreds of MB).\n"
  printf "\033[33m│\033[0m  On an older machine expect \033[1m5+ minutes\033[0m the first time.\n"
  printf "\033[33m│\033[0m  Near the end, pip will look \033[1mfrozen\033[0m while it unpacks torch —\n"
  printf "\033[33m│\033[0m  that is normal, not a crash. Please just let it finish.\n"
  printf "\033[33m│\033[0m  It only happens once; every run after this is instant.\n"
  printf "\033[1;33m└─────────────────────────────────────────────────────────────┘\033[0m\n"
  say "Setting up a Python env with torch + transformers (progress below)"
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
