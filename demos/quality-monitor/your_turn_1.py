# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Your turn (1) — write the segment alert rule
#
# Chapter 9: the alarm should fire when an evaluation score drops, and it
# should watch each use case or user segment, not just the global aggregate,
# because one broken workflow drowns in an average across all of them. The
# stub below watches the global average. On the real week it never fires,
# even though travel answers have been wrong since day 4. You fix that.
#
# THE TASK    Write segment_alerts(table). It gets the daily faithfulness
#             per segment and returns every (segment, day) where it fell
#             below THRESHOLD. Skip the "all" row: that's the global average.
#
# HOW TO WIN  Fill in segment_alerts() below, then run:
#                 python demos/quality-monitor/your_turn_1.py
#
# No model, no network, no key.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_monitor as qm  # noqa: E402

THRESHOLD = 0.85


# ═══ WRITE YOUR CODE HERE ══════════════════════════════════════════════════
def segment_alerts(table):
    """Return a list of (segment, day) pairs where faithfulness < THRESHOLD.

    table  {"all": {1: 0.99, 2: 0.98, ...},        <- the global average
            "travel": {1: 1.0, ..., 4: 0.60, ...}, <- one row per segment
            "expenses": {...}, ...}

    TODO: for each segment (every key except "all"), and each day in it,
          add (segment, day) to the result if the rate < THRESHOLD.
    """
    # --- your code goes here ---
    return [("all", d) for d, r in table["all"].items() if r < THRESHOLD]   # stub: global only
# ═══════════════════════════════════════════════════════════════════════════


def real_week():
    """The real week, scored as the monitor does, as {key: {day: rate}}."""
    table = qm.daily_quality(qm.score_sample(qm.load_traces()))
    return {k: {d: qm.rate(c) for d, c in row.items()} for k, row in table.items()}


GOLDEN = [   # (label, table, the alerts that should fire)
    ("a quiet week", {"all": {1: 0.97, 2: 0.98}, "travel": {1: 0.95, 2: 1.0},
                      "oncall": {1: 0.98, 2: 0.96}}, []),
    ("one segment dips on day 2", {"all": {1: 0.97, 2: 0.93}, "travel": {1: 0.95, 2: 0.70},
                                   "oncall": {1: 0.98, 2: 0.99}}, [("travel", 2)]),
    ("exactly at the line", {"all": {1: 0.90}, "oncall": {1: 0.85}}, []),
    ("the real week", real_week(), [("travel", d) for d in (4, 5, 6, 7)]),
]


def _show(pairs):
    """[("travel", 4), ("travel", 5)] -> "travel d4,5" """
    by = {}
    for seg, day in sorted(pairs):
        by.setdefault(seg, []).append(str(day))
    return "; ".join(f"{seg} d{','.join(ds)}" for seg, ds in by.items()) or "none"


def grade():
    qm.banner()
    print("  " + qm._c("2", "your turn (1) · write the segment alert rule\n"))
    print("  " + qm._c("2", f"Your segment_alerts(table) is called once per table below "
                            f"(threshold {THRESHOLD:.0%}).\n"))
    passed = 0
    for label, table, want in GOLDEN:
        got = sorted(tuple(x) for x in (segment_alerts(table) or []))
        ok = got == sorted(want)
        passed += ok
        mark = qm._c("32", "PASS") if ok else qm._c("31", "FAIL")
        print(f"  {mark}  {qm._c('2', 'in:')} {label:<26} {qm._c('2', '→')} "
              f"want {_show(want):<18} got {_show(got)}")

    print("\n  " + qm._c("2", "─" * 58))
    if passed == len(GOLDEN):
        week = GOLDEN[-1][1]
        lo = min(week["all"].values())
        print("  " + qm._c("32", f"SHIP — {passed}/{len(GOLDEN)}. Your alert watches each segment."))
        print("  " + qm._c("2", f"On the real week the global average never went below {lo:.0%}, so the"))
        print("  " + qm._c("2", "stub stayed quiet. Yours fires on travel from day 4, the day the index changed."))
        return 0
    print("  " + qm._c("31", f"BLOCKED — {passed}/{len(GOLDEN)}. Keep going."))
    print("  " + qm._c("2", "Edit segment_alerts() near the top of this file, then run it again."))
    print(qm._c("2",
        "\n  Hints (each reveals a little more):\n"
        '  1. Loop over the rows:   for seg, row in table.items():  (skip seg == "all")\n'
        "  2. Then over the days:   for day, r in row.items():\n"
        "  3. Collect the low ones: if r < THRESHOLD: fired.append((seg, day))\n"
        "     ...and return fired at the end.\n"))
    return 1


if __name__ == "__main__":
    sys.exit(grade())


# ═══ SPOILER — the solution, only if you're stuck ══════════════════════════
# def segment_alerts(table):
#     fired = []
#     for seg, row in table.items():
#         if seg == "all":
#             continue
#         for day, r in row.items():
#             if r < THRESHOLD:
#                 fired.append((seg, day))
#     return fired
