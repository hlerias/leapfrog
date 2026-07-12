#!/usr/bin/env bash
# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
#
# One-command setup for the grounded-Q&A demo, with honest feedback about the
# slow part. Then it runs the sample questions.
set -euo pipefail
cd "$(dirname "$0")"

printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
printf "  \033[1;96mLeapfrog Labs\033[0m \033[2m·\033[0m \033[1mAsk the handbook — setup\033[0m\n"
printf "  \033[2m%s\033[0m\n" "Grounded Q&A — cited, bounded, one job. Not a chatbot."
printf "  \033[2m%s\033[0m\n" "https://leapfrog.lerias.org"
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

if python -c "import sentence_transformers" >/dev/null 2>&1; then
  say "Using the sentence-transformers already in this environment"
else
  say "Setting up a Python env with the retrieval models' dependencies"
  printf "\n\033[1;33m┌─ Heads up: the next step is the slow one ────────────────────┐\033[0m\n"
  printf "\033[33m│\033[0m  Retrieval uses \033[1msentence-transformers\033[0m, which pulls in \033[1mPyTorch\033[0m\n"
  printf "\033[33m│\033[0m  — a big download (hundreds of MB). On an older machine expect\n"
  printf "\033[33m│\033[0m  \033[1m5+ minutes\033[0m, and pip looks frozen while it unpacks torch. Normal.\n"
  printf "\033[33m│\033[0m  It only happens once; runs after this start fast.\n"
  printf "\033[1;33m└──────────────────────────────────────────────────────────────┘\033[0m\n"
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -r requirements.txt
fi

say "Running the sample questions (first run also downloads ~180 MB of retrieval models)"
python ask.py --demo
