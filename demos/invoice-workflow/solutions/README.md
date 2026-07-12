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

## The labs — "did my run work?"

The nine labs in [`../../../labs/`](../../../labs/) aren't puzzles with hidden
answers — **they're complete, working code.** Running one *is* the answer. But
here's roughly what each should print, so you can confirm your run matched.
(Random ids, latencies, token counts, and any model's exact wording will differ
run to run — the **shape** and the **proof point** are what to check.) Every lab
now opens with a header line — its title and a one-line "what to watch" — before
the output below.

**`01_first_call.py`** — *needs a model* — the model's two-sentence answer, then
the meter:
```
Retrieval-augmented generation is ...
in=<n>  out=<n>  cost=$<0.0000xx>
```
Proof point: `out` tokens cost far more than `in`.

**`02_naive_rag.py`** — *no key (downloads a small model)*:
```
Q: Where is the NEXT offsite?
   best match (score 0.51): The Q3 offsite is in Lisbon on October 14th.
Q: What's the limit before I need sign-off?
   best match (score 0.15): Reimbursements over 500 EUR need VP approval.
```
Proof point: the scores are *low* and "next" isn't understood — naive top-1 is
fragile. (Scores vary slightly by model version.)

**`03_eval_gate.py`** — *no install* — deterministic:
```
PASS - Capital of Portugal?
PASS - 2 + 2 * 3 = ?
PASS - Who wrote the book Leapfrog?

score 100%  ->  SHIP
```

**`04_red_team_injection.py`** — *optional model* — prints the poisoned document
and explains the attack. With **no key** it tells you what to expect and exits
cleanly. **Set `LLM_API_KEY`** (or point at Ollama) and it sends both prompts and
prints the two replies — the naive one often replies `PWNED …`, the defended one
summarizes.

**`05_structured_output.py`** — *needs a model with JSON mode* — a validated object:
```
OK -> {'sentiment': 'negative', 'priority': 1, 'tags': ['outage', 'dashboard', ...]}
```
Proof point: data your code can branch on (values vary; sentiment negative,
priority low for the furious-customers ticket).

**`06_rag_rerank.py`** — *no key (downloads two small models)*:
```
The Q3 offsite is in Lisbon on October 14th.
```
Proof point: rerank surfaces the Q3 passage that naive top-1 (Lab 02) missed.

**`07_tool_use.py`** — *needs a model with tool calling* — the model's final
answer after the tool round-trip, e.g.:
```
Yes — the platform team (42) is larger than design (9).
```
Proof point: the model called your `get_headcount` function and composed the
answer from what you returned.

**`08_trace.py`** — *no install* — one JSON span:
```
{
  "id": "<8 hex chars>",
  "inputs": {"prompt": "Summarize Q3", "model": "gpt-4o-mini"},
  "tokens": {"in": 812, "out": 143},
  "ok": true,
  "latency_ms": <~150>
}
```

**`09_ship_tiny.py`** — *no key (downloads a small model)* — a bounded decision:
```
{
  "ticket": "The billing page has been down for an hour!",
  "policy_used": "Outages are P1 and page on-call immediately.",
  "route": "on-call",
  "priority": 1
}
```
Proof point: it grounds on a policy, returns a structured route, and stays inside
its allowlist. (`route` is `on-call` because "down" is in the ticket; `policy_used`
is whichever policy grounds closest.)

See [`labs/README.md`](../../../labs/README.md) for the fuller "what each one
proves" list.
