# Judge rubric — layer 3

The harness sends this rubric to the judge model (`--judge`) as its
instructions. The judge sees one case at a time: the **question**, the
**passages** the system retrieved, and the system's **response**. It replies
with JSON only:

```json
{"verdict": "pass", "reason": "one short sentence"}
```

The judge only sees cases that already passed layers 1 and 2 (the cheap
checks). Its job is the part those checks can't do: decide whether the answer
is actually right.

## Pass, if all of these are true

1. **Right.** The answer gives the correct answer to the question, using the
   passages.
2. **Sticks to the passages.** Every claim in the answer is supported by the
   passages. Nothing is added, changed or invented: no new numbers, no new
   rules, no new conditions.
3. **Answers what was asked.** It answers this question, not a different one.

A short answer is fine. "Monday mornings." is a complete answer to "When is
the on-call rotation handed over?". Do not fail an answer for being brief.

## Refusals

The system may reply "I couldn't find that in the handbook."

- **Pass** the refusal if none of the passages answer the question.
- **Fail** the refusal if one of the passages does answer the question: the
  system should have answered.

## Fail, if any of these are true

- The answer contradicts a passage, or changes a number, a name or a date.
- The answer adds a rule or a condition that is not in the passages, even if
  it sounds reasonable.
- The answer replies to a question the passages do not cover, instead of
  refusing.

Judge the content, not the style. A fluent, confident answer that is wrong is
a **fail**.
