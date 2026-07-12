# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (4) — write the eval gate
#
# The hardest and most important one. So far you've written STEPS inside the
# pipeline. Now you write the thing that decides whether the pipeline is even
# allowed to ship: an eval gate. It runs a golden set through a decision
# function, scores it, and returns SHIP or BLOCK. This is Chapter 8, in code —
# evals replace unit tests for systems that aren't deterministic.
#
# The twist: we grade YOUR gate two ways. A good gate must SHIP a pipeline
# that works AND BLOCK one that's quietly broken. A gate that passes
# everything is worse than no gate at all.
#
# THE TASK    Write run_eval(decider): score `decider` against GOLDEN and
#             return True to ship (>= 90% correct) or False to block.
#
# HOW TO WIN  Fill in run_eval() below, then run:
#                 python demos/invoice-workflow/your_turn_4.py
#
# No model, no network, no key. This is the gate that stops a bad deploy.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invoice_workflow as iw  # noqa: E402

THRESHOLD = 0.90   # ship only if at least this fraction of the golden set is right


def _inv(vendor, amount, total=None):
    total = amount if total is None else total
    return {"vendor": vendor, "invoice_number": vendor[:2].upper() + "-1",
            "invoice_date": "2026-03-01", "currency": "EUR",
            "line_items": [{"description": "services", "amount": amount}],
            "subtotal": amount, "tax": 0.0, "total": total}


# The golden set: invoices and the route the pipeline SHOULD give each.
GOLDEN = [
    (_inv("Acme", 100.0), "auto-approve"),                 # small, reconciles
    (_inv("Beta", 5000.0), "needs-approval"),              # over the 1000 limit
    (_inv("Gamma", 100.0, total=200.0), "hold-review"),    # numbers don't add up
    (_inv("Delta", 250.0), "auto-approve"),                # small, reconciles
    (_inv("Epsilon", 3000.0), "needs-approval"),           # over the 1000 limit
]


# ═══ WRITE YOUR EVAL GATE HERE ═════════════════════════════════════════════
def run_eval(decider):
    """`decider(inv)` returns a route string, e.g. "auto-approve". Score it
    against GOLDEN and return True to SHIP, False to BLOCK.

    TODO: 1) for each (invoice, expected_route) in GOLDEN, call decider(inv)
             and check whether it equals expected_route
          2) compute the fraction that matched
          3) return True if that fraction >= THRESHOLD, else False
    """
    # --- your code goes here ---
    return True   # stub: ships anything — exactly the bug an eval prevents
# ═══════════════════════════════════════════════════════════════════════════


# Two pipelines to grade your gate against:
def good_decider(inv):
    return iw.decide(inv)["route"]            # the real pipeline — should ship


def broken_decider(inv):
    return "auto-approve"                     # rubber-stamps everything — should block


def grade():
    iw.banner()
    print("  " + iw._c("2", "your turn (4) · write the eval gate\n"))
    print("  " + iw._c("2", f"Your run_eval(decider) scores a decider against this golden set "
                            f"(ship at ≥ {THRESHOLD:.0%}):"))
    for inv, exp in GOLDEN:
        print("  " + iw._c("2", f"    {inv['vendor']:<9} {inv['total']:>6.0f} EUR  →  should be {exp}"))
    print("  " + iw._c("2", "\n  We test YOUR gate on two deciders (these are the inputs):\n"))
    trials = [
        ("the real pipeline", good_decider, True, "SHIP"),
        ("a broken pipeline (auto-approves everything)", broken_decider, False, "BLOCK"),
    ]
    passed = 0
    for label, decider, want_ship, want_word in trials:
        got_ship = run_eval(decider) is True
        ok = got_ship == want_ship
        passed += ok
        mark = iw._c("32", "PASS") if ok else iw._c("31", "FAIL")
        got_word = "SHIP" if got_ship else "BLOCK"
        print(f"  {mark}  {iw._c('2', 'in:')} {label:<46} {iw._c('2', '→')} "
              f"want {want_word:<5} got {got_word}")

    print("\n  " + iw._c("2", "─" * 58))
    if passed == len(trials):
        print("  " + iw._c("32", f"SHIP — {passed}/{len(trials)}. Your gate works."))
        rate = sum(1 for inv, exp in GOLDEN if good_decider(inv) == exp) / len(GOLDEN)
        print("  " + iw._c("2", f"It ships the real pipeline ({rate:.0%} on the golden set) "
                                f"and blocks the rubber-stamp."))
        print("  " + iw._c("2", "Wire run_eval into CI and a bad prompt change can't merge. "
                                "That's the whole game."))
        return 0
    print("  " + iw._c("31", f"BLOCKED — {passed}/{len(trials)}. Keep going."))
    print("  " + iw._c("2", "Edit run_eval() near the top of this file, then run it again."))
    print(iw._c("2",
        "\n  Hints (each reveals a little more):\n"
        "  1. Count matches:  sum(1 for inv, exp in GOLDEN if decider(inv) == exp)\n"
        "  2. Make a rate:    matches / len(GOLDEN)\n"
        "  3. Gate on it:     return rate >= THRESHOLD\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def run_eval(decider):
#     matches = sum(1 for inv, expected in GOLDEN if decider(inv) == expected)
#     return matches / len(GOLDEN) >= THRESHOLD
