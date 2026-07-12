#!/usr/bin/env bash
# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
#
# One-command setup for the labs, with honest feedback about the slow part.
# (You can also do it by hand — see the README quick start.)
set -euo pipefail
cd "$(dirname "$0")"

printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
printf "  \033[1;96mLeapfrog Labs\033[0m \033[2m·\033[0m \033[1mSetup\033[0m\n"
printf "  \033[2m%s\033[0m\n" "The book is the why. This is where you build."
printf "  \033[2m%s\033[0m\n" "https://leapfrog.lerias.org"
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

say "Creating an isolated Python environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip

printf "\n\033[1;33m┌─ Heads up: the next step is the slow one ────────────────────┐\033[0m\n"
printf "\033[33m│\033[0m  The RAG labs use \033[1msentence-transformers\033[0m, which pulls in\n"
printf "\033[33m│\033[0m  \033[1mPyTorch\033[0m — a big download (hundreds of MB). On an older machine\n"
printf "\033[33m│\033[0m  expect \033[1m5+ minutes\033[0m the first time.\n"
printf "\033[33m│\033[0m  Near the end pip will look \033[1mfrozen\033[0m while it unpacks torch —\n"
printf "\033[33m│\033[0m  that is normal, not a crash. Please just let it finish.\n"
printf "\033[33m│\033[0m  It only happens once; after this the labs start instantly.\n"
printf "\033[1;33m└──────────────────────────────────────────────────────────────┘\033[0m\n"
say "Installing the lab dependencies (progress below)"
pip install -r requirements.txt

say "Done. Try a lab that needs no key at all:"
echo "    python labs/08_trace.py"
echo "    python labs/03_eval_gate.py"
