# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (2) — write the guardrail
#
# The alert told you something is wrong. Until the index is fixed, users keep
# getting confident, wrong travel answers. A runtime guardrail inspects each
# answer before it reaches the user (Ch 9). Chapter 7 says what it should
# produce when retrieval is weak: an honest "I don't know", not a confident
# fabrication. You write it.
#
# THE TASK    Write guard(resp). Return the response unchanged if it is fine,
#             or a refusal if it isn't:
#               - a refusal is fine, pass it through
#               - an answer with no source is not fine
#               - an answer that states numbers or names that are not in the
#                 passage it used is not fine
#             The eval harness already has both checks: eh.check_citation and
#             eh.check_grounded. Use them.
#
# HOW TO WIN  Fill in guard() below, then run:
#                 python demos/quality-monitor/your_turn_2.py
#
# No model, no network, no key.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_monitor as qm  # noqa: E402
from quality_monitor import eh  # noqa: E402  (the eval harness, already imported by the monitor)

REFUSAL = "I couldn't find that in the handbook."


# ═══ WRITE YOUR CODE HERE ══════════════════════════════════════════════════
def guard(resp):
    """Return resp if it is safe to show, else a refusal.

    resp  {"answer": str, "source": "travel.txt" or None, "refused": bool,
           "retrieved": [{"passage": ..., "source": ..., "score": ...}, ...]}

    Useful:  eh.check_citation({"expected_source": None}, resp) -> (ok, why)
             eh.check_grounded(resp)                            -> (ok, why)
    A refusal:  dict(resp, answer=REFUSAL, source=None, refused=True)

    TODO: 1) a refusal passes through
          2) if not cited, or not grounded, return a refusal
          3) otherwise return resp unchanged
    """
    # --- your code goes here ---
    return resp   # stub: lets every answer through
# ═══════════════════════════════════════════════════════════════════════════


def _resp(answer, passage, source="travel.txt", refused=False):
    return {"answer": answer, "source": source, "refused": refused,
            "retrieved": [{"passage": passage, "source": "travel.txt", "score": 5.0}]}


T1 = "Book travel through the booking tool at least three weeks ahead."
T3 = "Any single reimbursement over 500 EUR needs VP approval before you book."

GOLDEN = [   # (label, response, should it be stopped?)
    ("grounded answer", _resp("A trip over 500 EUR needs VP approval before you book.", T3), False),
    ("stale index, invented rule", _resp("Trips over 500 EUR need director approval.", T1), True),
    ("no source cited", _resp("Book at least three weeks ahead.", T1, source=None), True),
    ("an honest refusal", _resp(REFUSAL, T1, source=None, refused=True), False),
    ("paraphrase, same facts", _resp("Book it at least three weeks ahead, in the booking tool.", T1), False),
]


def grade():
    qm.banner()
    print("  " + qm._c("2", "your turn (2) · write the guardrail\n"))
    print("  " + qm._c("2", "Your guard(resp) is called once per response below.\n"))
    passed = 0
    for label, resp, want_stop in GOLDEN:
        out = guard(dict(resp)) or {}
        stopped = out.get("refused") is True and not resp["refused"]
        ok = stopped == want_stop
        passed += ok
        mark = qm._c("32", "PASS") if ok else qm._c("31", "FAIL")
        print(f"  {mark}  {qm._c('2', 'in:')} {label:<28} {qm._c('2', '→')} "
              f"want {'stop' if want_stop else 'pass':<5} got {'stop' if stopped else 'pass'}")

    print("\n  " + qm._c("2", "─" * 58))
    if passed == len(GOLDEN):
        print("  " + qm._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your guardrail works."))

        def as_guard(resp):
            out = guard(dict(resp))
            return out, (out.get("refused") is True and not resp["refused"]), ""
        traces = qm.load_traces()
        stopped = qm.replay_with_guard(traces, as_guard)
        travel = sum(1 for t, _ in stopped if qm.segment(t) == "travel" and t["day"] >= 4)
        print("  " + qm._c("2", f"Replayed over the real week, it stops {len(stopped)} answers, "
                                f"{travel} of them stale travel"))
        print("  " + qm._c("2", "answers from day 4. Those users get an honest refusal instead. The fix is"))
        print("  " + qm._c("2", "still the index; the guardrail is what protects users until it's fixed."))
        return 0
    print("  " + qm._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + qm._c("2", "Edit guard() near the top of this file, then run it again."))
    print(qm._c("2",
        "\n  Hints (each reveals a little more):\n"
        '  1. Pass refusals through first:  if resp["refused"]: return resp\n'
        '  2. Run both checks:  cited, _ = eh.check_citation({"expected_source": None}, resp)\n'
        "                       grounded, _ = eh.check_grounded(resp)\n"
        "  3. if not (cited and grounded):\n"
        "         return dict(resp, answer=REFUSAL, source=None, refused=True)\n"
        "     return resp\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def guard(resp):
#     if resp["refused"]:
#         return resp
#     cited, _ = eh.check_citation({"expected_source": None}, resp)
#     grounded, _ = eh.check_grounded(resp)
#     if not (cited and grounded):
#         return dict(resp, answer=REFUSAL, source=None, refused=True)
#     return resp
