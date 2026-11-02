# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (1) — write the citation check (layer 1)
#
# Layer 1 of the harness is programmatic: free, fast and objective. Chapter 9
# puts "does it contain the citation it was supposed to?" right there, and
# Chapter 7 says to make the model cite its sources. Here you write that check.
#
# THE TASK    Write citation_ok(item, resp). It gets one golden item and one
#             recorded response, and returns True if the citation is fine:
#               - a refusal cites nothing, and that is fine
#               - an answer must cite a source (resp["source"] is not None)
#               - if the golden item names an expected_source, the answer must
#                 cite exactly that file
#
# HOW TO WIN  Fill in citation_ok() below, then run:
#                 python demos/eval-harness/your_turn_1.py
#
# No model, no network, no key.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_harness as eh  # noqa: E402


# ═══ WRITE YOUR CODE HERE ══════════════════════════════════════════════════
def citation_ok(item, resp):
    """Return True if the response's citation is fine, False if not.

    item  golden item:  item["expected_source"] is a filename like
          "expenses.txt", or None for questions the handbook doesn't cover
    resp  response:     resp["refused"] (bool), resp["source"] (filename or None)

    TODO: 1) a refusal is fine (it cites nothing)
          2) an answer with no source fails
          3) an answer that cites a different file than expected_source fails
    """
    # --- your code goes here ---
    return True   # stub: accepts any citation, even a wrong one
# ═══════════════════════════════════════════════════════════════════════════


def _resp(answer, source, refused=False):
    return {"answer": answer, "source": source, "refused": refused, "retrieved": []}


Q08 = {"id": "q08", "question": "Who approves an expense reimbursement over 500 EUR?",
       "expected_source": "expenses.txt", "must_include": ["manager approval"],
       "should_refuse": False}

# The golden set for YOUR check: (item, response, should it pass?)
GOLDEN = [
    ("right file", Q08,
     _resp("Reimbursements over 500 EUR need manager approval.", "expenses.txt"), True),
    ("no source", Q08,
     _resp("Reimbursements over 500 EUR need manager approval.", None), False),
    ("wrong file", Q08,       # the right words, cited to the wrong handbook file
     _resp("Reimbursements over 500 EUR need manager approval.", "travel.txt"), False),
    ("a refusal", Q08,
     _resp("I couldn't find that in the handbook.", None, refused=True), True),
]


def grade():
    eh.banner()
    print("  " + eh._c("2", "your turn (1) · write the citation check (layer 1)\n"))
    print("  " + eh._c("2", "Your citation_ok(item, resp) is called once per response below,"))
    print("  " + eh._c("2", f"all for {Q08['id']}: \"{Q08['question']}\""))
    print("  " + eh._c("2", f"The fact lives in {Q08['expected_source']}.\n"))
    passed = 0
    for label, item, resp, want in GOLDEN:
        got = citation_ok(item, resp) is True
        ok = got == want
        passed += ok
        mark = eh._c("32", "PASS") if ok else eh._c("31", "FAIL")
        src = "refused" if resp["refused"] else f"source={resp['source']}"
        print(f"  {mark}  {eh._c('2', 'in:')} {label:<11} {src:<22} {eh._c('2', '→')} "
              f"want {'ok' if want else 'bad':<3}  got {'ok' if got else 'bad'}")

    print("\n  " + eh._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + eh._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your citation check works."))
        mis = GOLDEN[2][2]
        before = eh.layer1(Q08, mis, citation_check=lambda i, r: (True, "stub"))
        after = eh.layer1(Q08, mis, citation_check=lambda i, r: (
            citation_ok(i, r), "cited " + str(r["source"]) + ", expected " + str(i["expected_source"])))
        print("  " + eh._c("2", "Plugged into layer 1, the mis-cited answer now goes  ")
              + ("PASS" if before[0] else "FAIL") + " → " + ("PASS" if after[0] else "FAIL")
              + eh._c("2", f"  ({after[1]})."))
        print("  " + eh._c("2", "Right words, wrong source: \"cited\" is not the same as \"supported\" (Ch 7)."))
        return 0
    print("  " + eh._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + eh._c("2", "Edit citation_ok() near the top of this file, then run it again."))
    print(eh._c("2",
        "\n  Hints (each reveals a little more):\n"
        '  1. Handle refusals first:   if resp["refused"]: return True\n'
        '  2. No citation is a fail:   if not resp["source"]: return False\n'
        '  3. Then compare the files:  return resp["source"] == item["expected_source"]\n'
        "     (only when item[\"expected_source\"] is not None)\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def citation_ok(item, resp):
#     if resp["refused"]:
#         return True
#     if not resp["source"]:
#         return False
#     if item["expected_source"] is not None:
#         return resp["source"] == item["expected_source"]
#     return True
