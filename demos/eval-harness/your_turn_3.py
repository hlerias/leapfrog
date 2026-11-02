# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (3) — write the regression gate, per metric
#
# The gate is the thing that stands between a change and production (Ch 8).
# The tempting shortcut is to gate on ONE number: the average of the four
# signals. The stub below does exactly that, and it ships v2 — even though
# v2's faithfulness fell from 94% to 89%. A gain in one metric hid a loss in
# another. You write the gate that can't be fooled that way.
#
# THE TASK    Write gate_ok(candidate, baseline). Return True to SHIP, False
#             to BLOCK. Check EACH of the four metrics on its own:
#               - BLOCK if a metric is below its minimum (MINIMUM[key])
#               - BLOCK if a metric fell by more than TOLERANCE compared with
#                 the baseline (only when there is a baseline)
#
# HOW TO WIN  Fill in gate_ok() below, then run:
#                 python demos/eval-harness/your_turn_3.py
#
# No model, no network, no key.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_harness as eh  # noqa: E402

KEYS = [k for k, _ in eh.METRICS]   # "recall", "relevance", "faithfulness", "correctness"
MINIMUM = eh.MINIMUM                # e.g. MINIMUM["faithfulness"] == 0.90
TOLERANCE = eh.TOLERANCE            # 0.02 = a drop of up to 2 points is allowed


# ═══ WRITE YOUR CODE HERE ══════════════════════════════════════════════════
def gate_ok(candidate, baseline):
    """Return True to SHIP the candidate, False to BLOCK it.

    candidate  {"recall": {"rate": 1.0}, "faithfulness": {"rate": 0.889}, ...}
    baseline   the same shape for the version running today, or None

    TODO: for each key in KEYS:
            1) BLOCK if candidate[key]["rate"] < MINIMUM[key]
            2) if there is a baseline, BLOCK if the candidate fell by more
               than TOLERANCE:  candidate rate < baseline rate - TOLERANCE
          SHIP only if no metric blocked.
    """
    # --- your code goes here ---
    return eh.average_gate(candidate, baseline)   # stub: one number, the average
# ═══════════════════════════════════════════════════════════════════════════


def _m(recall, relevance, faithfulness, correctness):
    vals = dict(zip(KEYS, (recall, relevance, faithfulness, correctness)))
    return {k: {"rate": v} for k, v in vals.items()}


GOLD = eh.load_golden()
V1 = eh.metrics(eh.run_version(GOLD, eh.load_responses("v1"), eh.load_judge("v1")))
V2 = eh.metrics(eh.run_version(GOLD, eh.load_responses("v2"), eh.load_judge("v2")))

# The golden set for YOUR gate: (label, candidate, baseline, should it ship?)
GOLDEN = [
    ("v1 on its own (no baseline)", V1, None, True),
    ("v2 vs v1 (faithfulness 94% → 89%)", V2, V1, False),
    ("only gains, nothing falls", _m(1.0, 0.94, 0.95, 0.80), V1, True),
    ("a 1-point dip, inside tolerance", _m(1.0, 0.94, 0.935, 0.75), V1, True),
    ("relevance under its minimum", _m(1.0, 0.70, 0.95, 0.90), None, False),
]


def grade():
    eh.banner()
    print("  " + eh._c("2", "your turn (3) · write the regression gate, per metric\n"))
    print("  " + eh._c("2", "Your gate_ok(candidate, baseline) is called once per case below."))
    print("  " + eh._c("2", "minimums: " + ", ".join(f"{k} {MINIMUM[k]:.0%}" for k in KEYS)
                          + f"; tolerance {TOLERANCE * 100:.0f} points\n"))
    passed = 0
    for label, cand, base, want in GOLDEN:
        got = gate_ok(cand, base) is True
        avg = eh.average_gate(cand, base)
        ok = got == want
        passed += ok
        mark = eh._c("32", "PASS") if ok else eh._c("31", "FAIL")
        print(f"  {mark}  {eh._c('2', 'in:')} {label:<36} {eh._c('2', '→')} "
              f"want {'SHIP' if want else 'BLOCK':<5} got {'SHIP' if got else 'BLOCK':<5} "
              + eh._c("2", f"(average-only: {'SHIP' if avg else 'BLOCK'})"))

    print("\n  " + eh._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + eh._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your gate checks every metric."))
        print("  " + eh._c("2", f"v2's average moved {eh.average(V1):.1%} → {eh.average(V2):.1%}, "
                                "so the average-only gate ships it."))
        print("  " + eh._c("2", "Yours sees faithfulness fall and blocks it. Averages smooth it over (Ch 9)."))
        return 0
    print("  " + eh._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + eh._c("2", "Edit gate_ok() near the top of this file, then run it again."))
    print(eh._c("2",
        "\n  Hints (each reveals a little more):\n"
        "  1. Loop over the metrics:  for key in KEYS:  now = candidate[key][\"rate\"]\n"
        "  2. Below the minimum?      if now < MINIMUM[key]: return False\n"
        "  3. Fell too far?           if baseline and now < baseline[key][\"rate\"] - TOLERANCE:\n"
        "                                 return False\n"
        "     ...and after the loop:  return True\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def gate_ok(candidate, baseline):
#     for key in KEYS:
#         now = candidate[key]["rate"]
#         if now < MINIMUM[key]:
#             return False
#         if baseline and now < baseline[key]["rate"] - TOLERANCE:
#             return False
#     return True
