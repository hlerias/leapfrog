#!/usr/bin/env bash
# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
#
# Setup for the eval harness. The default path needs nothing but python3:
# it runs the tests, then the harness on the recorded responses.
#
#   ./setup.sh          no install — tests + the offline harness
#   ./setup.sh --live   also installs sentence-transformers, so that
#                       --live (and --nli) can run ask-the-docs for real
set -euo pipefail
cd "$(dirname "$0")"

printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
printf "  \033[1;96mLeapfrog Labs\033[0m \033[2m·\033[0m \033[1mEval harness — setup\033[0m\n"
printf "  \033[2m%s\033[0m\n" "How do you know it's working? Score it, gate it, check the judge."
printf "  \033[2m%s\033[0m\n" "https://leapfrog.lerias.org"
printf "\033[2m%s\033[0m\n" "────────────────────────────────────────────────────────────"
say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

say "Checking Python 3 (the default path needs no packages)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found — install Python 3.9 or newer, then re-run." >&2
  exit 1
fi
python3 --version
PY=python3

if [ "${1:-}" = "--live" ]; then
  if python3 -c "import sentence_transformers" >/dev/null 2>&1; then
    say "Using the sentence-transformers already in this environment"
  else
    say "Setting up a Python env with the retrieval models' dependencies"
    printf "\n\033[1;33m┌─ Heads up: the next step is the slow one ────────────────────┐\033[0m\n"
    printf "\033[33m│\033[0m  --live uses \033[1msentence-transformers\033[0m, which pulls in \033[1mPyTorch\033[0m\n"
    printf "\033[33m│\033[0m  — a big download (hundreds of MB). On an older machine expect\n"
    printf "\033[33m│\033[0m  \033[1m5+ minutes\033[0m, and pip looks frozen while it unpacks torch. Normal.\n"
    printf "\033[33m│\033[0m  It only happens once. The offline harness never needs it.\n"
    printf "\033[1;33m└──────────────────────────────────────────────────────────────┘\033[0m\n"
    python3 -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -q --upgrade pip
    pip install -r ../ask-the-docs/requirements.txt
    PY=python
  fi
fi

say "Running the tests (no models, no network)"
$PY test_harness.py

say "Running the harness: v2 vs v1 on the recorded responses (expect BLOCKED)"
$PY eval_harness.py || true

if [ "${1:-}" = "--live" ]; then
  say "Running the harness live against ask-the-docs (first run downloads ~180 MB of models)"
  $PY eval_harness.py --live || true
fi
