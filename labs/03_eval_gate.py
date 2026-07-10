# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 03 — A tiny eval gate                             Ch 8 & 9
# No API key — runs as-is with a stub answerer.
#
# WHAT IT IS    The smallest thing that stops a bad prompt from shipping.
# HOW IT WORKS  1) a golden set (question + must-include strings)
#               2) score each answer   3) gate on a threshold: SHIP or BLOCKED
# PROOF POINT   Swap the stub for your model, sabotage the prompt, re-run —
#               the score falls under 0.90 and the gate prints BLOCKED.
# WHY DO IT     Evals replace unit tests for non-deterministic systems; this
#               one gate in CI is what stands between you and a silent regression.
#
# Run:  python labs/03_eval_gate.py
GOLDEN = [
  {"q": "Capital of Portugal?",        "must_include": ["Lisbon"]},
  {"q": "2 + 2 * 3 = ?",               "must_include": ["8"]},
  {"q": "Who wrote the book Leapfrog?", "must_include": ["Hugo", "Lerias"]},
]

def score(ans, item):
    return all(k.lower() in ans.lower() for k in item["must_include"])

def run_eval(answer_fn, threshold=0.90):
    rows = [(it["q"], score(answer_fn(it["q"]), it)) for it in GOLDEN]
    rate = sum(ok for _, ok in rows) / len(rows)
    for q, ok in rows: print("PASS" if ok else "FAIL", "-", q)
    print(f"\nscore {rate:.0%}  ->  {'SHIP' if rate >= threshold else 'BLOCKED'}")
    return rate >= threshold

# plug in your real model from Lab 1 in place of this stub:
run_eval(lambda q: "Lisbon; 8; by Hugo Lerias")
