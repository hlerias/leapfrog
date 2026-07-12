# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (2) — write the policy step
#
# Exercise 1 had you write a CHECK (step 3 of the chain). This one is step 4:
# the DECIDE step, the bounded policy that picks the route. Right now every
# invoice shares one approval limit (EUR 1,000). Real teams don't work that
# way — a vendor you've paid for years can clear a bigger invoice than a
# stranger. You write that policy.
#
# THE TASK    Write approval_limit(inv): return the euro amount THIS invoice
#             is allowed to auto-approve up to. Trusted vendors get a higher
#             limit; everyone else keeps the default.
#
# HOW TO WIN  Fill in approval_limit() below, then run:
#                 python demos/invoice-workflow/your_turn_2.py
#             It grades your policy against a golden set (a tiny eval) and, on
#             success, shows a trusted vendor's invoice flip its route.
#
# No model, no network, no key — pure policy logic. This is "containment":
# the model never sets the limit; your code does.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invoice_workflow as iw  # noqa: E402

DEFAULT_LIMIT = 1000.0   # euros — the limit for an unknown vendor
TRUSTED_LIMIT = 5000.0   # euros — the limit for a trusted vendor
TRUSTED = {"acme hardware", "globex consulting"}   # long-standing vendors (lowercase)


# ═══ WRITE YOUR POLICY HERE ════════════════════════════════════════════════
def approval_limit(inv):
    """Return the euro limit this invoice can auto-approve up to.

    inv["vendor"] is the vendor name (a string, or None). Match it against
    TRUSTED case-insensitively.

    TODO: return TRUSTED_LIMIT when the vendor is trusted, else DEFAULT_LIMIT.
          Remember inv["vendor"] can be None.
    """
    # --- your code goes here ---
    return DEFAULT_LIMIT   # stub: everyone gets the default limit
# ═══════════════════════════════════════════════════════════════════════════


def _inv(vendor, amount):
    return {"vendor": vendor, "invoice_number": "X-1", "invoice_date": "2026-03-01",
            "currency": "EUR", "line_items": [{"description": "services", "amount": amount}],
            "subtotal": amount, "tax": 0.0, "total": amount}


# Golden set: (invoice, route it should take once YOUR policy is applied).
GOLDEN = [
    (_inv("ACME Hardware", 3000.0), "auto-approve"),      # trusted, under 5000
    (_inv("ACME Hardware", 200.0), "auto-approve"),       # trusted, small
    (_inv("Globex Consulting", 8000.0), "needs-approval"),  # trusted, over 5000
    (_inv("Random LLC", 1500.0), "needs-approval"),       # unknown, over 1000
    (_inv("Random LLC", 300.0), "auto-approve"),          # unknown, under 1000
]


def grade():
    iw.banner()
    print("  " + iw._c("2", "your turn (2) · write the policy step\n"))
    passed = 0
    for inv, want in GOLDEN:
        got = iw.decide(inv, approval_threshold=approval_limit)["route"]
        ok = got == want
        passed += ok
        mark = iw._c("32", "PASS") if ok else iw._c("31", "FAIL")
        print(f"  {mark}  {inv['vendor']:<18} {inv['total']:>8.0f} EUR   "
              f"want {want:<14} got {got}")

    print("\n  " + iw._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + iw._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your policy works."))
        trial = _inv("ACME Hardware", 3000.0)
        before = iw.decide(trial)["route"]                                  # default 1000
        after = iw.decide(trial, approval_threshold=approval_limit)["route"]  # your policy
        print("  " + iw._c("2", f"A €3,000 invoice from a trusted vendor goes  "
                                f"{before} → {after}  under your policy."))
        print("  " + iw._c("2", "You just wrote the containment step — the model never "
                                "sets the limit, your code does."))
        return 0
    print("  " + iw._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print(iw._c("2",
        "\n  Hints (each reveals a little more):\n"
        '  1. Normalise first:  name = (inv["vendor"] or "").lower()\n'
        "  2. Trusted?          name in TRUSTED\n"
        "  3. Return the limit: TRUSTED_LIMIT if trusted else DEFAULT_LIMIT\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def approval_limit(inv):
#     name = (inv.get("vendor") or "").lower()
#     return TRUSTED_LIMIT if name in TRUSTED else DEFAULT_LIMIT
