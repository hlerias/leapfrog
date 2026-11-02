# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (2) — write the faithfulness check (layer 2)
#
# Faithfulness, in Chapter 7's words: did the answer stick to the retrieved
# context, or wander off and invent? The harness answers that offline with a
# cheap, deterministic check. Here you write it.
#
# THE TASK    Write is_faithful(item, resp). Return True if the answer sticks
#             to the passage it used, False if not:
#               - a refusal claims nothing, so it is faithful
#               - an answer to a question that should be refused is NOT
#                 faithful: the handbook has nothing to support it
#               - otherwise every fact in item["must_include"] must appear in
#                 BOTH the passage it used and the answer (ignore upper/lower case)
#
# HOW TO WIN  Fill in is_faithful() below, then run:
#                 python demos/eval-harness/your_turn_2.py
#             Then watch your check catch the remote-work answer in the real gate.
#
# No model, no network, no key.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_harness as eh  # noqa: E402


# ═══ WRITE YOUR CODE HERE ══════════════════════════════════════════════════
def is_faithful(item, resp):
    """Return True if the response is faithful to the passage it used.

    item  golden item:  item["should_refuse"] (bool), item["must_include"] (list)
    resp  response:     resp["refused"] (bool), resp["answer"] (str),
                        resp["retrieved"][0]["passage"] = the passage it used

    TODO: 1) a refusal -> True
          2) an answer to a should_refuse question -> False
          3) each fact must be in the passage AND in the answer (lower-case both)
    """
    # --- your code goes here ---
    return True   # stub: trusts every answer
# ═══════════════════════════════════════════════════════════════════════════


GOLD = {g["id"]: g for g in eh.load_golden()}
V2 = eh.load_responses("v2")
# A response built on the WRONG passage: the answer has the facts, the passage doesn't.
WRONG_PASSAGE = dict(V2["q09"], retrieved=[
    {"passage": "The Q2 offsite was in Berlin on April 9th.", "source": "offsites.txt", "score": 4.2}])

# The golden set for YOUR check: (label, item, response, faithful?)
GOLDEN = [
    ("q01 grounded answer", GOLD["q01"], V2["q01"], True),
    ("q06 says 50 EUR, passage says 40", GOLD["q06"], V2["q06"], False),
    ("q16 a refusal", GOLD["q16"], V2["q16"], True),
    ("q17 answers remote work", GOLD["q17"], V2["q17"], False),
    ("q09 facts not in its passage", GOLD["q09"], WRONG_PASSAGE, False),
    ("q11 paraphrased, still grounded", GOLD["q11"], V2["q11"], True),
]


def grade():
    eh.banner()
    print("  " + eh._c("2", "your turn (2) · write the faithfulness check (layer 2)\n"))
    print("  " + eh._c("2", "Your is_faithful(item, resp) is called once per case below"))
    print("  " + eh._c("2", "(real recorded v2 responses, plus one built on the wrong passage):\n"))
    passed = 0
    for label, item, resp, want in GOLDEN:
        got = is_faithful(item, resp) is True
        ok = got == want
        passed += ok
        mark = eh._c("32", "PASS") if ok else eh._c("31", "FAIL")
        print(f"  {mark}  {eh._c('2', 'in:')} {label:<34} {eh._c('2', '→')} "
              f"want {'faithful' if want else 'NOT':<8}  got {'faithful' if got else 'NOT'}")

    print("\n  " + eh._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + eh._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your faithfulness check works."))
        print("  " + eh._c("2", "Now the real gate, v2 vs v1, with each check plugged into layer 2:\n"))
        golden = eh.load_golden()
        for name, fn in (("the stub (trusts everything)", lambda i, r: (True, "stub")),
                         ("your is_faithful()", lambda i, r: (
                             is_faithful(i, r), eh.check_faithful(i, r)[1]))):
            ms = {v: eh.metrics(eh.run_version(golden, eh.load_responses(v), eh.load_judge(v),
                                               faithful_check=fn)) for v in ("v1", "v2")}
            problems = eh.gate(ms["v2"], ms["v1"])
            f1, f2 = ms["v1"]["faithfulness"]["rate"], ms["v2"]["faithfulness"]["rate"]
            print(f"  {name:<30} faithfulness {f1:.0%} → {f2:.0%}   ", end="")
            if problems:
                cases = {c["id"]: c for c in eh.run_version(
                    golden, eh.load_responses("v2"), eh.load_judge("v2"), faithful_check=fn)}
                print(eh._c("31", "BLOCKED"))
                print("    " + eh._c("31", eh.headline(problems[0], cases)))
            else:
                print(eh._c("32", "SHIP"))
        print("\n  " + eh._c("2", "With the stub, v2's invented remote-work policy ships. With yours, it can't."))
        return 0
    print("  " + eh._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + eh._c("2", "Edit is_faithful() near the top of this file, then run it again."))
    print(eh._c("2",
        "\n  Hints (each reveals a little more):\n"
        '  1. Two early returns:  if resp["refused"]: return True\n'
        '                         if item["should_refuse"]: return False\n'
        '  2. Get the text:       passage = resp["retrieved"][0]["passage"].lower()\n'
        '                         answer = resp["answer"].lower()\n'
        "  3. Check every fact:   return all(f.lower() in passage and f.lower() in answer\n"
        '                                    for f in item["must_include"])\n'))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def is_faithful(item, resp):
#     if resp["refused"]:
#         return True
#     if item["should_refuse"]:
#         return False
#     passage = resp["retrieved"][0]["passage"].lower()
#     answer = resp["answer"].lower()
#     return all(f.lower() in passage and f.lower() in answer
#                for f in item["must_include"])
