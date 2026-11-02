# 🙈 Solutions — try it yourself first

**Run the exercise and take a real swing before you read this.** The point of
`your_turn_*.py` is the moment your own code turns `BLOCKED` into `SHIP`.
Each exercise has hints that reveal a little more each time, and the same
solution sits at the bottom of each file, so you rarely need this page.

Still here? Here is each solution and *why* it works.

---

## Exercise 1 — the citation check · `your_turn_1.py`

**Task:** layer 1. An answer must cite a source, and it must cite the file
the golden set expects.

```python
def citation_ok(item, resp):
    if resp["refused"]:
        return True
    if not resp["source"]:
        return False
    if item["expected_source"] is not None:
        return resp["source"] == item["expected_source"]
    return True
```

**Why:** a refusal cites nothing, and that is correct, so it passes. An answer
with no source fails. An answer that cites the wrong file fails too, even when
the words are right: the expense rule lives in `expenses.txt`, not
`travel.txt`. Chapter 7 calls this the gap between "cited" and "supported".
It is a free, objective check, which is why it runs first.

---

## Exercise 2 — the faithfulness check · `your_turn_2.py`

**Task:** layer 2. Did the answer stick to the passage it used?

```python
def is_faithful(item, resp):
    if resp["refused"]:
        return True
    if item["should_refuse"]:
        return False
    passage = resp["retrieved"][0]["passage"].lower()
    answer = resp["answer"].lower()
    return all(f.lower() in passage and f.lower() in answer
               for f in item["must_include"])
```

**Why:** a refusal claims nothing unsupported, so it is faithful. An answer to
a question the handbook doesn't cover has nothing to stand on, so it is not.
For every other answer, each key fact must be in **both** the passage and the
answer. "In the answer" alone isn't enough: an answer can hold the right
words while the passage it used says something else. With this check in place
the gate sees v2's remote-work answer and blocks it. With the stub, v2 ships.

This is the cheap, deterministic version. Chapter 9 also names semantic
entailment against the retrieved context. Try `eval_harness.py --nli` for
that (it needs `sentence-transformers`).

---

## Exercise 3 — the regression gate · `your_turn_3.py`

**Task:** gate each metric on its own: below its minimum, or fell by more
than the tolerance, means BLOCK.

```python
def gate_ok(candidate, baseline):
    for key in KEYS:
        now = candidate[key]["rate"]
        if now < MINIMUM[key]:
            return False
        if baseline and now < baseline[key]["rate"] - TOLERANCE:
            return False
    return True
```

**Why:** the stub gates on the average of the four signals. v2's correctness
went up by about 6 points while its faithfulness fell by about 6, so the
average barely moved (90.8% → 91.0%) and the stub ships it. Chapter 9:
averages smooth it over. Checking every metric against its own floor and its
own baseline means a loss in one can't hide behind a gain in another. The
tolerance lets small noise through (a 1-point dip ships) without letting a
real drop through.

---

## Exercise 4 — close the loop · `your_turn_4.py`

**Task:** turn a flagged production failure into a golden case.

```python
def new_golden_case():
    return {"id": "q19",
            "question": PRODUCTION_FAILURE["question"],
            "expected_source": None,
            "must_include": [],
            "should_refuse": True}
```

**Why:** the handbook says nothing about pets, so the right answer is an
honest refusal. That makes this case look like q17 and q18: no expected
source, no facts to include, `should_refuse: true`. The trap is copying
`offsites.txt` from the bot's citation. The bot cited it, but the file
doesn't answer the question. Once the case is in the set, v3's answer counts
as unfaithful and the gate blocks it.

This is the feedback loop from Chapter 9: production traces go to people,
they label real failures, and those failures go back into the golden set.
The chapter's experiment asks you to curate five. This was one.
