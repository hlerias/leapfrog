# 🙈 Solutions — try it yourself first

**Run the exercise and take a real swing before you read this.** The point of
`your_turn_*.py` is the moment your own code turns `BLOCKED` into `SHIP`.
Each exercise has hints that reveal a little more each time, and the same
solution sits at the bottom of each file, so you rarely need this page.

Still here? Here is each solution and *why* it works.

---

## Exercise 1 — the segment alert rule · `your_turn_1.py`

**Task:** fire for every segment and day where faithfulness fell below the
threshold. Not on the global average.

```python
def segment_alerts(table):
    fired = []
    for seg, row in table.items():
        if seg == "all":
            continue
        for day, r in row.items():
            if r < THRESHOLD:
                fired.append((seg, day))
    return fired
```

**Why:** the stub watches the `"all"` row, the global average. Travel is
about one request in six, so even when a third of its answers go wrong the
average only dips from 99% to about 92%, above the 85% line. The stub stays
quiet all week. Checking each segment on its own catches travel on day 4, the
day the index changed. Chapter 9: watch drift at the level of the prompt, use
case or user segment, not just the global aggregate, because one broken
workflow drowns in an average across all of them.

The "exactly at the line" case checks that you used `<`: a segment at 85% is
at the threshold, not below it.

---

## Exercise 2 — the guardrail · `your_turn_2.py`

**Task:** before the user sees an answer, turn it into a refusal if it is
uncited or not grounded in its passage.

```python
def guard(resp):
    if resp["refused"]:
        return resp
    cited, _ = eh.check_citation({"expected_source": None}, resp)
    grounded, _ = eh.check_grounded(resp)
    if not (cited and grounded):
        return dict(resp, answer=REFUSAL, source=None, refused=True)
    return resp
```

**Why:** a refusal is already safe, so it passes through. For an answer, the
guard runs the same two cheap checks the monitor uses: did it cite a source,
and are the numbers and names it states in the passage it used? The stale
travel answers fail the second one: "Trips over 500 EUR need director
approval" was built on a passage about booking three weeks ahead, which says
nothing about 500 EUR. That answer becomes "I couldn't find that in the
handbook." A paraphrase that keeps the passage's facts still passes.

This is Chapter 9's third touchpoint: a runtime guardrail that blocks or
rewrites a response before it reaches the user. It is the safety net, not the
fix. Those users now get an honest "I don't know" instead of a wrong answer,
and the fix is still to rebuild the index.
