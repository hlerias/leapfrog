# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# make_traces.py — generate traces/week.jsonl (synthetic, for this demo)
#
# One made-up week of ask-the-docs production traffic, as trace trees grown
# from Lab 08's single span: request → retrieval span → generation span. The
# attribute names follow the OpenTelemetry GenAI conventions where they exist
# (gen_ai.*), plus a few app.* attributes of our own.
#
# The scenario baked in:
#   - on day 4 the retrieval index is rebuilt (app.index_version changes),
#     and the rebuild picks up an old copy of travel.txt that lacks two of its
#     rules (VP approval over 500 EUR, rental cars). Travel questions about
#     those rules now retrieve the wrong passage, and the model answers anyway.
#   - every other segment is untouched; latency and error rate stay flat all
#     week; the prompt version and the model never change.
#
# Fixed seed, so the file is identical every time you run it.
#
# Run:  python demos/quality-monitor/make_traces.py   (rewrites traces/week.jsonl)

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "traces", "week.jsonl")
SEED = 2026
DAYS = ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29",
        "2026-10-30", "2026-10-31", "2026-11-01"]
STALE_FROM_DAY = 4                         # 2026-10-29: the index rebuild
REQUESTS_PER_DAY = (130, 145)
MODEL = "llama3.2"
PROMPT_VERSION = "prompt-2026-09-12"
INDEX_BEFORE, INDEX_AFTER = "hb-2026-10-01", "hb-2026-10-29"
REFUSAL = "I couldn't find that in the handbook."
THRESHOLD = 0.0                            # ask.py's refusal threshold

# The handbook sentences (each one is checked against ../ask-the-docs/handbook by the tests).
P = {
    "E1": ("Submit expenses within 30 days of the spend.", "expenses.txt"),
    "E2": ("Meals are capped at 40 EUR per day while travelling.", "expenses.txt"),
    "E3": ("Alcohol is not reimbursable.", "expenses.txt"),
    "E4": ("Reimbursements over 500 EUR need manager approval.", "expenses.txt"),
    "O1": ("The Q2 offsite was in Berlin on April 9th.", "offsites.txt"),
    "O2": ("The Q3 offsite is in Lisbon on October 14th.", "offsites.txt"),
    "O3": ("Offsite attendance is optional but strongly encouraged.", "offsites.txt"),
    "O4": ("Travel to offsites is booked through the normal travel tool.", "offsites.txt"),
    "C1": ("Outages are P1 and page the on-call engineer immediately.", "oncall.txt"),
    "C2": ("On-call rotations run weekly, handed over on Monday mornings.", "oncall.txt"),
    "C3": ("Escalate to the incident commander if an outage is not contained within 30 minutes.", "oncall.txt"),
    "C4": ("Billing questions go to finance, not to engineering.", "oncall.txt"),
    "T1": ("Book travel through the booking tool at least three weeks ahead.", "travel.txt"),
    "T2": ("Flights under six hours are economy class; longer flights may be premium economy.", "travel.txt"),
    "T3": ("Any single reimbursement over 500 EUR needs VP approval before you book.", "travel.txt"),
    "T4": ("Rental cars require prior manager approval.", "travel.txt"),
}

# segment -> share of traffic
SEGMENTS = {"expenses": 0.34, "oncall": 0.26, "offsites": 0.24, "travel": 0.16}

# segment -> [(weight, [questions], passage, [others retrieved], good answer, [a wrong answer] or None)]
# The wrong answer is what the model says on the rare day it slips (3% of those questions).
INTENTS = {
    "expenses": [
        (3, ["How long do I have to submit expenses?", "What's the deadline for expense claims?"],
         "E1", ["E4", "E2"], "Submit expenses within 30 days of the spend.", None),
        (3, ["What's the meal limit when I'm travelling?", "How much can I spend on food per day?"],
         "E2", ["E3", "T2"], "Meals are capped at 40 EUR per day while travelling.",
         ["Meals are capped at 50 EUR per day while travelling."]),
        (2, ["Can I expense a bottle of wine?", "Is alcohol reimbursable?"],
         "E3", ["E2", "E1"], "No. Alcohol is not reimbursable.", None),
        (2, ["Who approves a reimbursement over 500 EUR?"],
         "E4", ["T3", "E1"], "Reimbursements over 500 EUR need manager approval.", None),
    ],
    "oncall": [
        (3, ["What priority is an outage?", "Does an outage page someone?"],
         "C1", ["C3", "C2"], "Outages are P1 and page the on-call engineer immediately.",
         ["Outages are P2 and page the on-call engineer within the hour."]),
        (2, ["When is the on-call rotation handed over?"],
         "C2", ["C1", "C3"], "Rotations are handed over on Monday mornings.", None),
        (2, ["What if an outage isn't contained after half an hour?"],
         "C3", ["C1", "C2"], "Escalate to the incident commander after 30 minutes.", None),
        (2, ["Who answers billing questions?"],
         "C4", ["C1", "E4"], "Billing questions go to finance, not to engineering.", None),
    ],
    "offsites": [
        (4, ["Where is the next offsite?", "When is the Q3 offsite?"],
         "O2", ["O1", "O3"], "The next offsite is the Q3 offsite, in Lisbon on October 14th.",
         ["The next offsite is in Porto on October 14th."]),
        (2, ["Where was the Q2 offsite?"],
         "O1", ["O2", "O3"], "The Q2 offsite was in Berlin on April 9th.", None),
        (2, ["Do I have to attend the offsite?"],
         "O3", ["O4", "O2"], "No. Offsite attendance is optional but strongly encouraged.", None),
        (2, ["How do I book travel to an offsite?"],
         "O4", ["T1", "O2"], "Travel to offsites is booked through the normal travel tool.", None),
    ],
    "travel": [
        (2, ["How far ahead should I book travel?", "When should I book my flights?"],
         "T1", ["O4", "T3"], "Book travel through the booking tool at least three weeks ahead.", None),
        (1, ["What class can I fly on a long flight?"],
         "T2", ["T1", "O4"], "Flights under six hours are economy class; longer flights may be premium economy.", None),
        (3, ["Who approves a trip over 500 EUR?", "My trip costs 800 EUR, who signs it off?"],
         "T3", ["E4", "T1"], "A trip over 500 EUR needs VP approval before you book.", None),
        (2, ["Do I need approval to rent a car?", "Can I book a rental car?"],
         "T4", ["E4", "T1"], "Yes. Rental cars need prior manager approval.", None),
    ],
}

# After the day-4 rebuild, the old travel.txt has no T3 and no T4. Questions
# about them retrieve what IS there, with low scores, and the model answers anyway.
STALE = {
    "T3": (["T1", "T2", "E4"], ["Trips over 500 EUR need director approval before you book.",
                                "Anything over 500 EUR needs sign-off from your team lead."]),
    "T4": (["T2", "T1", "O4"], ["Rental cars are fine without approval for up to 3 days.",
                                "You can rent a car without approval if it costs under 200 EUR."]),
}


def pick(rng, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


def hexid(rng, n):
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def make_trace(rng, day, n):
    seg = pick(rng, list(SEGMENTS), list(SEGMENTS.values()))
    intents = INTENTS[seg]
    weight, questions, key, others, good, wrong = pick(rng, intents, [i[0] for i in intents])
    question = rng.choice(questions)
    stale = day >= STALE_FROM_DAY and key in STALE

    if stale:
        keys, bluffs = STALE[key]
        scores = sorted([round(rng.uniform(-0.4, 1.8), 2), round(rng.uniform(-4.0, -2.0), 2),
                         round(rng.uniform(-6.5, -4.5), 2)], reverse=True)
        hits = [dict(zip(("passage", "source"), P[k]), score=s) for k, s in zip(keys, scores)]
        answer = rng.choice(bluffs)
    else:
        scores = [round(rng.uniform(4.5, 8.8), 2), round(rng.uniform(-1.0, 3.5), 2),
                  round(rng.uniform(-6.0, -2.0), 2)]
        hits = [dict(zip(("passage", "source"), P[k]), score=s) for k, s in zip([key] + others, scores)]
        answer = rng.choice(wrong) if (wrong and rng.random() < 0.03) else good
    refused = hits[0]["score"] < THRESHOLD
    if refused:
        answer = REFUSAL

    error = rng.random() < 0.003
    r_ms = rng.randint(18, 64)
    g_ms = 0 if error else int(rng.lognormvariate(6.45, 0.28))
    in_tok = rng.randint(170, 260)
    out_tok = 0 if error or refused else rng.randint(18, 46)
    hour, minute, sec = rng.randint(7, 19), rng.randint(0, 59), rng.randint(0, 59)
    tid = hexid(rng, 16)
    req_id, ret_id, gen_id = hexid(rng, 8), hexid(rng, 8), hexid(rng, 8)

    gen_attr = {"gen_ai.operation.name": "chat", "gen_ai.request.model": MODEL,
                "gen_ai.usage.input_tokens": in_tok, "gen_ai.usage.output_tokens": out_tok,
                "app.prompt_version": PROMPT_VERSION, "latency_ms": g_ms, "error": error}
    if error:
        gen_attr["error.type"] = "upstream 503"
    else:
        gen_attr.update({"output.answer": answer,
                         "output.source": None if refused else hits[0]["source"],
                         "output.refused": refused})
    return {
        "trace_id": tid, "day": day, "timestamp": f"{DAYS[day - 1]}T{hour:02d}:{minute:02d}:{sec:02d}Z",
        "spans": [
            {"span_id": req_id, "parent_id": None, "name": "request",
             "attributes": {"app.segment": seg, "app.route": "primary", "input.question": question,
                            "latency_ms": r_ms + g_ms + 9, "error": error}},
            {"span_id": ret_id, "parent_id": req_id, "name": "retrieval",
             "attributes": {"app.index_version": INDEX_AFTER if day >= STALE_FROM_DAY else INDEX_BEFORE,
                            "retrieval.top_k": 3, "retrieval.documents": hits,
                            "latency_ms": r_ms, "error": False}},
            {"span_id": gen_id, "parent_id": req_id, "name": "generation", "attributes": gen_attr},
        ],
    }


def build():
    rng = random.Random(SEED)
    rows = [{"_note": "synthetic, for this demo: one made-up week of ask-the-docs production "
                      "traffic, generated by make_traces.py (fixed seed). Not real traffic."}]
    for day in range(1, len(DAYS) + 1):
        for n in range(rng.randint(*REQUESTS_PER_DAY)):
            rows.append(make_trace(rng, day, n))
    head, body = rows[:1], rows[1:]
    body.sort(key=lambda r: r["timestamp"])        # in time order, as a tracer would export them
    return head + body


def write(path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in build():
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


if __name__ == "__main__":
    out = write(sys.argv[1] if len(sys.argv) > 1 else OUT)
    print(f"wrote {out}")
