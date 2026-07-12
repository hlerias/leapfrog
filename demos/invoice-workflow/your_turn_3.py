# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (3) — a check that remembers
#
# Exercises 1 and 2 judged each invoice on its own. This one is harder: some
# checks need MEMORY. A vendor submits the same invoice twice — an honest
# mistake or a quiet fraud — and paying both is a double payment. To catch it,
# your check has to remember what it has already seen.
#
# THE TASK    Write a check that HOLDS any invoice whose number you've already
#             seen this run. The first time a number appears it passes; the
#             second time, it's a duplicate — hold it.
#
# HOW TO WIN  Fill in student_check() below, then run:
#                 python demos/invoice-workflow/your_turn_3.py
#             It feeds invoices IN ORDER (order matters now) and grades you.
#
# No model, no network, no key. New idea: a check can carry state.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invoice_workflow as iw  # noqa: E402

seen = set()   # invoice numbers seen so far — use this to remember


# ═══ WRITE YOUR CHECK HERE ═════════════════════════════════════════════════
def student_check(inv):
    """A check with memory. Return {"ok": True} to pass, or
    {"ok": False, "text": "..."} to HOLD.

    Use the module-level `seen` set above to remember invoice numbers.

    TODO: if inv["invoice_number"] is already in `seen`, HOLD it (duplicate).
          Otherwise, add it to `seen` and pass — so the NEXT copy is caught.
    """
    num = inv.get("invoice_number")
    # --- your code goes here ---
    return {"ok": True, "text": "duplicate check: not written yet"}
# ═══════════════════════════════════════════════════════════════════════════


def _inv(vendor, number, amount=100.0):
    return {"vendor": vendor, "invoice_number": number, "invoice_date": "2026-03-01",
            "currency": "EUR", "line_items": [{"description": "services", "amount": amount}],
            "subtotal": amount, "tax": 0.0, "total": amount}


# An ORDERED stream of invoices: (invoice, should your check HOLD it?).
GOLDEN = [
    (_inv("ACME", "AC-100"), False),      # first time      -> pass
    (_inv("Globex", "GB-200"), False),    # first time      -> pass
    (_inv("ACME", "AC-100"), True),       # same as #1      -> HOLD (duplicate)
    (_inv("Initech", "IN-300"), False),   # first time      -> pass
    (_inv("Globex", "GB-200"), True),     # same as #2      -> HOLD (duplicate)
]


def grade():
    iw.banner()
    print("  " + iw._c("2", "your turn (3) · a check that remembers\n"))
    seen.clear()                          # fresh run
    passed = 0
    for i, (inv, should_hold) in enumerate(GOLDEN, 1):
        r = student_check(inv) or {}
        held = r.get("ok") is False
        ok = held == should_hold
        passed += ok
        mark = iw._c("32", "PASS") if ok else iw._c("31", "FAIL")
        want = "HOLD" if should_hold else "pass"
        got = "HOLD" if held else "pass"
        print(f"  {mark}  #{i}  {inv['vendor']:<9} {inv['invoice_number']:<8}"
              f"  want {want}, yours said {got}")

    print("\n  " + iw._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + iw._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your check remembers."))
        seen.clear()
        dup = _inv("Fresh", "FR-999")
        first = iw.decide(dup, extra_checks=[student_check])["route"]
        second = iw.decide(dup, extra_checks=[student_check])["route"]
        print("  " + iw._c("2", f"Seen twice in the real pipeline, FR-999 goes  "
                                f"{first} → {second}."))
        print("  " + iw._c("2", "Some checks are stateless; this one had to remember. "
                                "You just wrote one that does."))
        return 0
    print("  " + iw._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + iw._c("2", "Edit student_check() near the top of this file, then run it again."))
    print(iw._c("2",
        "\n  Hints (each reveals a little more):\n"
        "  1. Check membership first:  if num in seen: return {\"ok\": False, ...}\n"
        "  2. Otherwise remember it:   seen.add(num)\n"
        "  3. ...then pass:            return {\"ok\": True}\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def student_check(inv):
#     num = inv.get("invoice_number")
#     if num in seen:
#         return {"ok": False, "text": f"duplicate of an invoice already seen ({num})"}
#     seen.add(num)
#     return {"ok": True, "text": "first time seen"}
