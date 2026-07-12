# 🙈 Solutions — try it yourself first

**Seriously: run the exercise and take a real swing before you read this.** The
whole point of `your_turn*.py` is the moment your own code turns `BLOCKED` into
`SHIP`. Peeking skips the only part that sticks. The exercises also have
progressive hints, and the same solution sits at the bottom of each file — so
you rarely need this page at all.

Still here? Fine. Here's each solution and *why* it works.

---

## Exercise 1 — write a check · `your_turn.py`

**Task:** hold any invoice dated after today (`TODAY = "2026-07-12"`).

```python
def student_check(inv):
    date = inv.get("invoice_date")
    if not date:
        return {"ok": True, "text": "no date to check"}
    return {"ok": date <= TODAY,
            "text": "dated in the future" if date > TODAY else "date ok"}
```

**Why:** ISO date strings (`YYYY-MM-DD`) compare correctly with `<`/`>`, so no
date parsing is needed. Missing dates pass (a different check already handles
missing fields); everything else passes only if it's on or before today — so a
`2027` date fails this check and the invoice is held.

---

## Exercise 2 — write the policy · `your_turn_2.py`

**Task:** trusted vendors get a higher auto-approve limit than strangers.

```python
def approval_limit(inv):
    name = (inv.get("vendor") or "").lower()
    return TRUSTED_LIMIT if name in TRUSTED else DEFAULT_LIMIT
```

**Why:** normalise the vendor to lower-case (and guard `None`) before checking
membership in `TRUSTED`. Return the bigger limit for trusted vendors, the default
for everyone else. The pipeline — not the model — then routes on that limit. This
is *containment*: your code sets the bound.

---

## Exercise 3 — a check that remembers · `your_turn_3.py`

**Task:** hold an invoice whose number you've already seen this run (duplicate).

```python
def student_check(inv):
    num = inv.get("invoice_number")
    if num in seen:
        return {"ok": False, "text": f"duplicate of an invoice already seen ({num})"}
    seen.add(num)
    return {"ok": True, "text": "first time seen"}
```

**Why:** the new idea is *state*. The `seen` set (provided above the stub)
remembers every number the check has processed. Check membership first — if it's
already there, it's a duplicate, so hold it. Otherwise record it and pass, so the
*next* copy is caught. Order matters, because the first occurrence is legitimate.

---

## Exercise 4 — write the eval gate · `your_turn_4.py`

**Task:** score a decision function against the golden set; ship at ≥ 90%.

```python
def run_eval(decider):
    matches = sum(1 for inv, expected in GOLDEN if decider(inv) == expected)
    return matches / len(GOLDEN) >= THRESHOLD
```

**Why:** run each golden invoice through `decider`, count how many routes match
the expected one, divide by the total, and gate on the threshold. The exercise
grades your gate two ways on purpose: a good gate must **ship** a pipeline that
works *and* **block** one that rubber-stamps everything. A gate that passes
everything is worse than no gate — which is exactly why the stub (`return True`)
fails. Wire `run_eval` into CI and a bad change can't merge. That's Chapter 8.

---

## What about the labs?

The nine labs in [`../../../labs/`](../../../labs/) aren't puzzles with hidden
answers — **they're complete, working code.** Running one *is* the answer: read
the header (what it is, how it works, its proof point), run it, and watch the
proof point happen. See [`labs/README.md`](../../../labs/README.md) for what each
one demonstrates. The only "blanks" are the two labs with a `# plug in your
model` stub — that's a wiring point (drop in your Lab 1 call), not a puzzle.
