#!/usr/bin/env bash
# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
#
# Invoice Workflow demo — one command, everything configured.
# Clone the repo, run this, and it will: make a Python env, install Ollama if
# needed, pull a small local model, and run the invoice workflow end to end.
# No API key, no cost. Re-running is fast — each step is skipped if already done.
set -euo pipefail
cd "$(dirname "$0")"

# Model is chosen to match the hardware further below (GPU -> 3B, CPU-only ->
# 1B). Pin one explicitly to skip the auto-pick:  LLM_MODEL=llama3.2 ./run.sh
GPU_MODEL="llama3.2"        # 3B — a GPU handles it comfortably
CPU_MODEL="llama3.2:1b"     # CPU-only: ~2-4x faster, same quality for extraction
OLLAMA_URL="http://localhost:11434"

say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

# True only for a GPU Ollama can actually use for inference. This box, for
# example, has an Intel iGPU + an old AMD dGPU but neither is usable — so we
# deliberately do NOT look at lspci, only at real acceleration stacks.
_has_usable_gpu() {
  # NVIDIA / CUDA
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L 2>/dev/null | grep -qi 'GPU'; then
    return 0
  fi
  # Apple Silicon (Metal)
  if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    return 0
  fi
  # AMD ROCm — only if the ROCm stack is actually installed and sees a GPU
  if [ -e /dev/kfd ] && command -v rocminfo >/dev/null 2>&1 \
     && rocminfo 2>/dev/null | grep -q 'Device Type:.*GPU'; then
    return 0
  fi
  return 1
}

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

# 1b. Pick a model that matches the hardware --------------------------------
say "Checking for a usable GPU"
if [ -n "${LLM_MODEL:-}" ]; then
  MODEL="$LLM_MODEL"
  echo "    using pinned model: $MODEL (LLM_MODEL is set)"
elif _has_usable_gpu; then
  MODEL="$GPU_MODEL"
  echo "    GPU detected — using '$MODEL'"
else
  MODEL="$CPU_MODEL"
  echo "    no usable GPU — using the lighter '$MODEL' (faster on CPU, same quality here)"
fi

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

# Download + unpack Ollama into ~/.local, best-effort. Ollama ships the Linux
# build as .tar.zst now (older builds were .tgz) — try the current format, then
# fall back to the old one. Returns non-zero on any failure so the caller can
# switch to transformers instead of aborting. Called from an `if`, so set -e is
# relaxed inside it and a failed download won't kill the script.
_install_ollama_linux() {
  local arch="$1" base="https://ollama.com/download" tmp="/tmp/leapfrog-ollama"
  mkdir -p "$HOME/.local"
  if curl -fsSL --max-time 300 "$base/ollama-linux-${arch}.tar.zst" -o "$tmp.tar.zst" 2>/dev/null \
     && tar --zstd -C "$HOME/.local" -xf "$tmp.tar.zst" 2>/dev/null; then
    :
  elif curl -fsSL --max-time 300 "$base/ollama-linux-${arch}.tgz" -o "$tmp.tgz" 2>/dev/null \
       && tar -C "$HOME/.local" -xzf "$tmp.tgz" 2>/dev/null; then
    :
  else
    return 1
  fi
  [ -x "$HOME/.local/bin/ollama" ]
}

if command -v ollama >/dev/null 2>&1; then
  # already installed — skip the download entirely
  say "Ollama already installed — skipping download"
elif _ollama_reachable; then
  say "Ollama not found — trying to install it into \$HOME/.local (no sudo needed)"
  os="$(uname -s)"; arch="$(uname -m)"
  case "$arch" in x86_64|amd64) arch=amd64 ;; aarch64|arm64) arch=arm64 ;; esac
  if [ "$os" = "Linux" ]; then
    if _install_ollama_linux "$arch"; then
      export PATH="$HOME/.local/bin:$PATH"
      echo "    installed to $HOME/.local/bin/ollama"
    else
      echo "    Ollama download/unpack failed — using the transformers backend instead." >&2
      _use_transformers "$@"
    fi
  elif [ "$os" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install ollama
    else
      echo "    macOS without Homebrew — using the transformers backend instead." >&2
      echo "    (For the faster Ollama path, install it from https://ollama.com/download and re-run.)" >&2
      _use_transformers "$@"
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
# Match the EXACT tag, not just the family: llama3.2:1b is a different model
# from llama3.2:latest, and matching only "llama3.2" would wrongly skip the
# pull when a sibling tag is already present (then the API 404s at run time).
# A bare name (no ":tag") is stored by ollama as ":latest", so normalise that.
_want="$MODEL"; case "$_want" in *:*) ;; *) _want="$_want:latest" ;; esac
if ! ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$_want"; then
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
