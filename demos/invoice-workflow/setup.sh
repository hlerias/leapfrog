#!/usr/bin/env bash
# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
#
# Invoice Workflow demo — full setup for a fresh machine.
# Installs EVERYTHING the demo needs, then runs it:
#   1. system tools   (python3, venv, pip, curl, git)
#   2. Ollama         (a local model runner — no API key, no cost)
#   3. a small model  (llama3.2 by default — this is the big download)
#   4. Python deps    (into an isolated .venv)
#   5. runs the workflow against the sample invoices
#
# Safe to re-run: every step is skipped if it is already satisfied.
# Works on Linux (apt / dnf / pacman) and macOS (Homebrew). On Windows,
# run this inside WSL — see ../../docs/setup-wsl.md.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${LLM_MODEL:-llama3.2}"

# --- branded banner --------------------------------------------------------
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
printf "  \033[1;96mLeapfrog Labs\033[0m \033[2m·\033[0m \033[1mInvoice Workflow — setup\033[0m\n"
printf "  \033[2m%s\033[0m\n" "The book is the why. This is where you build."
printf "  \033[2m%s\033[0m\n" "https://leapfrog.lerias.org"
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"

say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
need() { command -v "$1" >/dev/null 2>&1; }

# --- privilege helper (use sudo only when needed and available) ------------
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if need sudo; then SUDO="sudo"; fi
fi

# --- 1. system prerequisites ----------------------------------------------
install_prereqs() {
  local os; os="$(uname -s)"
  if [ "$os" = "Darwin" ]; then
    if ! need brew; then
      echo "Homebrew is required on macOS. Install it from https://brew.sh then re-run." >&2
      exit 1
    fi
    need python3 || brew install python
    need git || brew install git
    return
  fi
  # Linux — pick the package manager
  if need apt-get; then
    $SUDO apt-get update -y
    $SUDO apt-get install -y python3 python3-venv python3-pip curl git
  elif need dnf; then
    $SUDO dnf install -y python3 python3-pip curl git
  elif need pacman; then
    $SUDO pacman -Sy --noconfirm python python-pip curl git
  elif need zypper; then
    $SUDO zypper install -y python3 python3-venv python3-pip curl git
  else
    echo "Could not detect your package manager. Please install manually:" >&2
    echo "  python3, python3-venv, python3-pip, curl, git" >&2
    exit 1
  fi
}

say "Checking system tools (python3, venv, pip, curl, git)"
if need python3 && python3 -m venv --help >/dev/null 2>&1 && need curl && need git; then
  echo "    already present — nothing to install"
else
  install_prereqs
fi

# --- 2-5. hand off to the runner, which installs Ollama + model + deps -----
# run.sh is idempotent: it creates the venv, installs Ollama and the model if
# they are missing, then runs the workflow. Pass through any extra args.
say "Handing off to run.sh (Ollama + model + Python deps + run)"
exec ./run.sh "$@"
