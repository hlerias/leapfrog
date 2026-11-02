# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (4) — close the loop
#
# Chapter 9 says the practice that matters most is not the golden set itself
# but the feedback loop around it: production traces go to people, they label
# real failures, and those failures go back into the golden set for the next
# cycle. Your coverage then grows out of what actually breaks.
#
# The setup: v3 (a new reranker) runs on a small canary slice of traffic. On
# the 18 golden questions it behaves exactly like v1, so the gate ships it.
# But a reviewer flagged one production trace from the canary (below). You
# turn that failure into a golden case. Then the gate catches v3.
#
# THE TASK    Write new_golden_case(). Return ONE golden item, in the same
#             shape as the lines in golden.jsonl:
#               {"id", "question", "expected_source", "must_include", "should_refuse"}
#             Read the failure, check the handbook, and label it correctly.
#
# HOW TO WIN  Fill in new_golden_case() below, then run:
#                 python demos/eval-harness/your_turn_4.py
#
# No model, no network, no key.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_harness as eh  # noqa: E402

# The flagged production trace (synthetic, for this demo).
PRODUCTION_FAILURE = {
    "version": "v3",
    "question": "Can I bring my dog to the Lisbon offsite?",
    "retrieved": [
        {"passage": "The Q3 offsite is in Lisbon on October 14th.", "source": "offsites.txt", "score": 1.4},
        {"passage": "Offsite attendance is optional but strongly encouraged.", "source": "offsites.txt", "score": -2.9},
        {"passage": "Travel to offsites is booked through the normal travel tool.", "source": "offsites.txt", "score": -4.1},
    ],
    "answer": "Yes. Pets are welcome at the Q3 offsite in Lisbon on October 14th.",
    "source": "offsites.txt",
    "refused": False,
    "reviewer": "The handbook says nothing about pets. This answer is invented.",
}


# ═══ WRITE YOUR CODE HERE ══════════════════════════════════════════════════
def new_golden_case():
    """Return one new golden item for the flagged question.

    Look at the existing lines in golden.jsonl, and at the handbook in
    ../ask-the-docs/handbook/. Does the handbook answer this question?

    TODO: return a dict with these five keys:
            "id"               a new id, not already in golden.jsonl
            "question"         the question from PRODUCTION_FAILURE
            "expected_source"  the handbook file that answers it, or None
            "must_include"     the facts a right answer must contain (a list)
            "should_refuse"    True if the handbook doesn't cover it
    """
    # --- your code goes here ---
    return None   # stub: the failure never makes it back into the golden set
# ═══════════════════════════════════════════════════════════════════════════


REFUSAL = "I couldn't find that in the handbook."


def _versions(extra):
    """v1 and v3 on the golden set. On the 18 existing questions v3 answers
    exactly like v1; the only difference is the flagged question."""
    v1 = eh.load_responses("v1")
    v3 = {k: dict(r, version="v3") for k, r in v1.items()}
    if extra:
        cid = extra["id"]
        v1[cid] = dict(PRODUCTION_FAILURE, id=cid, version="v1", threshold=0.0,
                       retrieved=[dict(h, score=h["score"] - 2.0) for h in PRODUCTION_FAILURE["retrieved"]],
                       answer=REFUSAL, source=None, refused=True)
        v3[cid] = dict(PRODUCTION_FAILURE, id=cid, threshold=0.0)
    return v1, v3


def _gate(golden, extra):
    v1, v3 = _versions(extra)
    judge = eh.load_judge("v1")
    m1 = eh.metrics(eh.run_version(golden, v1, judge))
    cases3 = eh.run_version(golden, v3, judge)
    m3 = eh.metrics(cases3)
    return eh.gate(m3, m1), {c["id"]: c for c in cases3}, m1, m3


def _shape_checks(case, golden):
    ids = {g["id"] for g in golden}
    ok_dict = isinstance(case, dict)
    c = case if ok_dict else {}
    return [
        ("it is a dict with the five keys", ok_dict and set(c) >= {
            "id", "question", "expected_source", "must_include", "should_refuse"}),
        ("the id is new", ok_dict and isinstance(c.get("id"), str) and c.get("id") not in ids),
        ("the question is the flagged one", c.get("question") == PRODUCTION_FAILURE["question"]),
        ("should_refuse is right", c.get("should_refuse") is True),
        ("expected_source is right", "expected_source" in c and c.get("expected_source") is None),
        ("must_include is right", c.get("must_include") == []),
    ]


def grade():
    eh.banner()
    print("  " + eh._c("2", "your turn (4) · close the loop\n"))
    f = PRODUCTION_FAILURE
    print("  " + eh._c("2", f"flagged production trace ({f['version']}, canary):"))
    print(f"    question:  {f['question']}")
    print(f"    answer:    {f['answer']}   [{f['source']}]")
    print("    " + eh._c("33", f"reviewer:  {f['reviewer']}"))

    golden = eh.load_golden()
    problems, _, _, _ = _gate(golden, None)
    print("\n  " + eh._c("2", f"Today the gate runs v3 vs v1 on the {len(golden)} golden questions:  ")
          + (eh._c("31", "BLOCKED") if problems else eh._c("32", "SHIP")
             + eh._c("2", " — it can't see a failure that isn't in the set.")))

    case = new_golden_case()
    print("\n  " + eh._c("2", "Your new_golden_case() is checked like this:\n"))
    checks = _shape_checks(case, golden)
    passed = 0
    for label, ok in checks:
        passed += bool(ok)
        print(f"  {eh._c('32', 'PASS') if ok else eh._c('31', 'FAIL')}  {label}")

    print("\n  " + eh._c("2", "─" * 58))
    if passed == len(checks):
        problems, cases, m1, m3 = _gate(golden + [case], case)
        print("  " + eh._c("2", f"Re-run with {len(golden) + 1} golden questions, v3 vs v1:"))
        for p in problems:
            print("  " + eh._c("31", "BLOCKED — " + eh.headline(p, cases)))
        if problems:
            print("\n  " + eh._c("32", f"SHIP — {passed}/{len(checks)}. The loop is closed."))
            print("  " + eh._c("2", "One real failure, labelled and curated back into the set, and the gate"))
            print("  " + eh._c("2", "now catches v3 before it leaves the canary. Ch 9's experiment asks for five."))
            return 0
        print("  " + eh._c("31", "The case looks right, but the gate still ships v3. Check must_include."))
        return 1
    print("  " + eh._c("31", f"BLOCKED — {passed}/{len(checks)}. Keep going."))
    print("  " + eh._c("2", "Edit new_golden_case() near the top of this file, then run it again."))
    print(eh._c("2",
        "\n  Hints (each reveals a little more):\n"
        "  1. Look at q17 and q18 in golden.jsonl: they are questions the handbook\n"
        "     doesn't cover. Then search offsites.txt for anything about pets.\n"
        "  2. The bot cited offsites.txt, but citing a file doesn't make it the answer.\n"
        "     Nothing in the handbook answers this, so expected_source is None.\n"
        '  3. return {"id": "q19", "question": PRODUCTION_FAILURE["question"],\n'
        '             "expected_source": None, "must_include": [], "should_refuse": True}\n'))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def new_golden_case():
#     return {"id": "q19",
#             "question": PRODUCTION_FAILURE["question"],
#             "expected_source": None,      # the handbook doesn't cover pets
#             "must_include": [],
#             "should_refuse": True}        # the right answer is an honest refusal
