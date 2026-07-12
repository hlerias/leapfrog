# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn — write a step in the chain
#
# The invoice workflow decides each invoice by running a CHAIN of small checks
# (see reconcile() in invoice_workflow.py). Each check looks at one extracted
# invoice and says: pass, or HOLD it for a human. The route is only ever
# auto-approve if EVERY check passes. That is the whole safety model.
#
# THE TASK    Add one new check to the chain. Accounts-payable teams never
#             auto-pay an invoice dated in the FUTURE — you haven't received
#             the goods yet. The pipeline doesn't check dates. You write it.
#
# HOW TO WIN  Fill in student_check() below, then run:
#                 python demos/invoice-workflow/your_turn.py
#             It grades your check against a golden set (a tiny eval) and
#             prints PASS / FAIL, then shows your check flip a real decision.
#
# No model, no network, no key — this is pure pipeline logic.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invoice_workflow as iw  # noqa: E402

TODAY = "2026-07-12"   # pretend today is this date (ISO, YYYY-MM-DD)


# ═══ WRITE YOUR CHECK HERE ═════════════════════════════════════════════════
def student_check(inv):
    """A step in the chain. Look at one extracted invoice and decide.

    Return:  {"ok": True}                     -> invoice passes this check
             {"ok": False, "text": "reason"}  -> HOLD it for a human

    `inv` is a dict; inv["invoice_date"] is an ISO string like "2026-03-14"
    (or None). ISO dates compare correctly with < and >, so no parsing needed.

    TODO: return ok=False (HOLD) when the invoice date is AFTER TODAY.
          If there is no date, let it pass — another check handles missing
          fields, so this step should only judge dates it can actually see.
    """
    # --- your code goes here ---
    return {"ok": True, "text": "future-date check: not written yet"}
# ═══════════════════════════════════════════════════════════════════════════


# A tiny golden set: (extracted invoice, should YOUR check HOLD it?).
# This is an eval — it grades your step the way Chapter 8 grades a prompt.
def _inv(vendor, date, amount):
    return {"vendor": vendor, "invoice_number": vendor[:3].upper() + "-1",
            "invoice_date": date, "currency": "EUR",
            "line_items": [{"description": "services", "amount": amount}],
            "subtotal": amount, "tax": 0.0, "total": amount}


GOLDEN = [
    (_inv("ACME", "2026-03-14", 100.0), False),    # past date   -> should pass
    (_inv("Globex", TODAY, 50.0), False),          # today       -> should pass
    (_inv("FutureCorp", "2027-01-05", 200.0), True),   # future  -> should HOLD
    (_inv("NoDate", None, 10.0), False),           # no date     -> should pass
]


def grade():
    iw.banner()
    print("  " + iw._c("2", "your turn · write a step in the chain\n"))
    print("  " + iw._c("2", "Your student_check(inv) is called once for each invoice below."))
    print("  " + iw._c("2", f"inv is a dict (inv['invoice_date'], inv['vendor'], …). Today is {TODAY}.\n"))
    passed = 0
    for inv, should_hold in GOLDEN:
        r = student_check(inv) or {}
        held = r.get("ok") is False
        ok = held == should_hold
        passed += ok
        mark = iw._c("32", "PASS") if ok else iw._c("31", "FAIL")
        want = "HOLD" if should_hold else "pass"
        got = "HOLD" if held else "pass"
        inp = f"date={str(inv['invoice_date']):<11} {inv['vendor']:<11}"
        print(f"  {mark}  {iw._c('2', 'in:')} {inp} {iw._c('2', '→')} "
              f"want {want:<4} got {got}")

    print("\n  " + iw._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + iw._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your check works."))
        fut = GOLDEN[2][0]
        before = iw.decide(fut)["route"]
        after = iw.decide(fut, extra_checks=[student_check])["route"]
        print("  " + iw._c("2", f"Plugged into the real pipeline, the future-dated "
                                f"invoice now goes  {before} → {after}."))
        print("  " + iw._c("2", "You just wrote a step in the chain that catches what "
                                "the model can't. That's the job."))
        return 0
    print("  " + iw._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + iw._c("2", "Edit student_check() near the top of this file, then run it again."))
    print(iw._c("2",
        "\n  Hints (each reveals a little more):\n"
        '  1. To hold an invoice, return {"ok": False, "text": "dated in the future"}.\n'
        '  2. Handle the None date first:  if not inv["invoice_date"]: return {"ok": True}\n'
        '  3. Then compare the strings:     inv["invoice_date"] > TODAY  means future.\n'))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def student_check(inv):
#     date = inv.get("invoice_date")
#     if not date:
#         return {"ok": True, "text": "no date to check"}
#     return {"ok": date <= TODAY,
#             "text": "dated in the future" if date > TODAY else "date ok"}
