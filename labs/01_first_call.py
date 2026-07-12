# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 01 — Your first call, and read the meter          Ch 1 & 5
# Needs a model: a real API key OR a local Ollama (free).
#
# WHAT IT IS    One real model call — and the exact tokens and cost it ran up.
# HOW IT WORKS  1) POST one message to an OpenAI-compatible endpoint
#               2) print the reply   3) price it from the usage token counts
# PROOF POINT   The `usage` block is the whole point: output tokens cost far
#               more than input, and that printed figure is real money.
# WHY DO IT     You can't reason about AI cost until you've watched one
#               call's meter move — everything downstream is this, scaled.
#
# Run:  export LLM_API_KEY=...   then   python labs/01_first_call.py
# pip install requests
import os, requests

print("── Leapfrog Labs · Lab 01 — Your first call, and read the meter ──")
print("Watch the meter at the end: output tokens cost far more than input.\n")

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
API_KEY  = os.environ.get("LLM_API_KEY")
MODEL    = os.environ.get("LLM_MODEL", "gpt-4o-mini")
PRICE_IN, PRICE_OUT = 0.15, 0.60                # $ per 1M tokens — set YOUR model's

if not API_KEY:
    raise SystemExit(
        "This lab needs a model. Two free-or-paid options:\n"
        "  • Hosted:       export LLM_API_KEY=sk-...\n"
        "  • Free / local: run Ollama, then\n"
        "                  export LLM_BASE_URL=http://localhost:11434/v1\n"
        "                  export LLM_API_KEY=ollama  LLM_MODEL=llama3.2\n"
        "See the README, then re-run.")

try:
    r = requests.post(f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": MODEL, "messages": [
            {"role": "user", "content": "In two sentences, what is retrieval-augmented generation?"}]},
        timeout=60).json()
except requests.exceptions.RequestException as e:
    raise SystemExit(f"Could not reach the model at {BASE_URL}.\n  {e}\n"
                     "Is the endpoint up (or Ollama running)? See the README.")

if "choices" not in r:
    raise SystemExit(f"Unexpected response from the model:\n  {r}")

print("The model's answer:")
print(" ", r["choices"][0]["message"]["content"])

u = r["usage"]
cost = u["prompt_tokens"] / 1e6 * PRICE_IN + u["completion_tokens"] / 1e6 * PRICE_OUT
print("\nThe meter for this one call:")
print(f"  input tokens : {u['prompt_tokens']}")
print(f"  output tokens: {u['completion_tokens']}   <- the pricey side")
print(f"  cost         : ${cost:.6f}")
