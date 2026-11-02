# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Eval harness — how do you know it's working?           Ch 7, 8 & 9
# No API key, no install — runs as-is on recorded responses (--offline).
#
# WHAT IT IS    A pre-deployment gate for the ask-the-docs demo. A teammate
#               lowers the refusal threshold so it answers more questions.
#               Is that better? The harness decides with data, not a hunch.
# HOW IT WORKS  1) a golden set: questions with known-good criteria
#               2) run two versions (v1 = today, v2 = the proposed change)
#               3) score in layers, cheap and free first, the judge last
#               4) compare the four signals per metric and gate: SHIP or BLOCKED
#               5) --calibrate: check the judge against human labels
# PROOF POINT   v2 answers more questions and its correctness goes UP, but its
#               faithfulness falls from 94% to 89%. The per-metric gate prints
#               BLOCKED and names the case. A gate on the average would ship it.
# WHY DO IT     "Evaluations replace unit tests" (Ch 8). You cannot assert
#               output == expected for open text, so you score it against a
#               golden set and gate on the result, metric by metric.
#
# Run:  python demos/eval-harness/eval_harness.py              (v2 vs v1 → BLOCKED)
#       python demos/eval-harness/eval_harness.py --version v1 (v1 alone → SHIP)
#       python demos/eval-harness/eval_harness.py --calibrate  (check the judge)
#
# Exit code: 0 = SHIP, 1 = BLOCKED, so it works as a CI check.

import argparse
import glob
import json
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ASK_DIR = os.path.join(HERE, "..", "ask-the-docs")          # the system under test
HANDBOOK = os.path.join(ASK_DIR, "handbook")                 # read in place, never copied

# --- the gate's config (env vars override) ----------------------------------
# A metric BLOCKS the change if it is below its minimum, OR if it fell by more
# than TOLERANCE compared with the baseline version.
METRICS = [                                     # the four signals from Chapter 7
    ("recall",       "retrieval recall"),       # did you fetch the right chunks at all?
    ("relevance",    "context relevance"),      # was what you fetched actually on point?
    ("faithfulness", "faithfulness"),           # did the answer stick to the context?
    ("correctness",  "correctness"),            # was the final answer actually right?
]
MINIMUM = {
    "recall":       float(os.environ.get("EVAL_MIN_RECALL", "0.85")),
    "relevance":    float(os.environ.get("EVAL_MIN_RELEVANCE", "0.80")),
    "faithfulness": float(os.environ.get("EVAL_MIN_FAITHFULNESS", "0.90")),
    "correctness":  float(os.environ.get("EVAL_MIN_CORRECTNESS", "0.70")),
}
TOLERANCE = float(os.environ.get("EVAL_TOLERANCE", "0.02"))  # max drop vs baseline (0.02 = 2 points)

# The one thing that differs between the two versions: ask.py's refusal
# threshold (ASK_THRESHOLD). v2 lowers it so that more questions get answered.
VERSIONS = {"v1": 0.0, "v2": -2.0}

# Optional judge model — same env vars as every other Leapfrog lab.
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("LLM_API_KEY", "ollama")
MODEL = os.environ.get("LLM_MODEL", "llama3.2")


# --- data -------------------------------------------------------------------
def load_jsonl(path):
    """Read a .jsonl file. Lines with a "_note" key are notes, not data."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                if "_note" not in row:
                    rows.append(row)
    return rows


def load_golden(path=None):
    return load_jsonl(path or os.path.join(HERE, "golden.jsonl"))


def load_responses(version):
    return {r["id"]: r for r in load_jsonl(os.path.join(HERE, "responses", f"{version}.jsonl"))}


def load_judge(version):
    return {r["id"]: r for r in load_jsonl(os.path.join(HERE, "judge", f"{version}.jsonl"))}


def load_humans():
    return {r["id"]: r for r in load_jsonl(os.path.join(HERE, "humans.jsonl"))}


def handbook_files():
    return {os.path.basename(p): open(p, encoding="utf-8").read()
            for p in sorted(glob.glob(os.path.join(HANDBOOK, "*.txt")))}


def _has(text, fact):
    return fact.lower() in (text or "").lower()


def used_passage(resp):
    """The passage the answer was built from: the top retrieved one."""
    return resp["retrieved"][0]["passage"] if resp.get("retrieved") else ""


def is_right_passage(item, hit):
    """A retrieved passage is 'right' if it comes from the expected file and
    holds every must_include fact."""
    return (hit["source"] == item["expected_source"]
            and all(_has(hit["passage"], f) for f in item["must_include"]))


# --- layer 1: programmatic checks (free, objective) -------------------------
def check_refusal(item, resp):
    """Refused exactly when the golden set says it should?"""
    if item["should_refuse"] and not resp["refused"]:
        return False, "answered a question it should refuse"
    if not item["should_refuse"] and resp["refused"]:
        return False, "refused a question the handbook answers"
    return True, "refused, as it should" if resp["refused"] else "answered"


def check_citation(item, resp):
    """Did the answer cite a source, and the expected one?"""
    if resp["refused"]:
        return True, "a refusal cites nothing"
    if not resp.get("source"):
        return False, "no source cited"
    if item["expected_source"] and resp["source"] != item["expected_source"]:
        return False, f"cited {resp['source']}, expected {item['expected_source']}"
    return True, f"cited {resp['source']}"


def layer1(item, resp, citation_check=check_citation):
    for check in (check_refusal, citation_check):
        ok, why = check(item, resp)
        if not ok:
            return False, why
    return True, "ok"


# --- layer 2: grounded — is the answer supported by the passage it used? ----
def check_faithful(item, resp):
    """Offline, deterministic version: every must_include fact must appear in
    BOTH the passage and the answer. A refusal claims nothing, so it is
    faithful. Any answer to a should_refuse question is not."""
    if resp["refused"]:
        return True, "a refusal claims nothing unsupported"
    if item["should_refuse"]:
        return False, "answered a question it should refuse"
    passage = used_passage(resp)
    for fact in item["must_include"]:
        if not _has(passage, fact):
            return False, f"'{fact}' is not in the passage it used"
        if not _has(resp["answer"], fact):
            return False, f"the passage says '{fact}', the answer doesn't"
    return True, "the key facts are in the passage and in the answer"


def nli_faithful_check():
    """Optional (--nli): add semantic entailment, from Chapter 9's second
    family of methods. Needs sentence-transformers; imported lazily."""
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        raise SystemExit("--nli needs sentence-transformers:\n"
                         "  pip install -r ../ask-the-docs/requirements.txt   (or ./setup.sh --live)")
    model = CrossEncoder("cross-encoder/nli-deberta-v3-small")
    labels = {v.lower(): int(k) for k, v in model.model.config.id2label.items()}

    def check(item, resp):
        ok, why = check_faithful(item, resp)
        if not ok or resp["refused"]:
            return ok, why
        scores = model.predict([(used_passage(resp), resp["answer"])])[0]
        best = max(labels, key=lambda name: scores[labels[name]])
        if best != "entailment":
            return False, f"entailment model: the passage does not support the answer ({best})"
        return True, "the passage entails the answer"
    return check


# --- layer 3: the judge — only on cases that passed layers 1 and 2 ----------
def judge_live(item, resp):
    """Ask a model to score one case against rubric.md. Standard library only."""
    import urllib.request
    rubric = open(os.path.join(HERE, "rubric.md"), encoding="utf-8").read()
    passages = "\n".join(f"- [{h['source']}] {h['passage']}" for h in resp.get("retrieved", []))
    user = (f"Question: {item['question']}\n\nRetrieved passages:\n{passages}\n\n"
            f"Response: {resp['answer']}\n\nReply with JSON only.")
    body = json.dumps({"model": MODEL, "temperature": 0,
                       "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": rubric},
                                    {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            content = json.loads(r.read())["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        out = json.loads(content[start:end + 1])
        verdict = "pass" if str(out.get("verdict", "")).lower().startswith("pass") else "fail"
        return {"id": item["id"], "verdict": verdict, "reason": str(out.get("reason", ""))}
    except Exception as e:
        raise SystemExit(f"--judge: no usable reply from {MODEL} at {BASE_URL} ({e}).\n"
                         "Is the model running? Without --judge the recorded verdicts are used.")


# --- score one case, then a whole version -----------------------------------
def score_case(item, resp, verdicts, citation_check=check_citation,
               faithful_check=check_faithful, judge=None):
    """Run the layers in order, cheap first. The judge is only consulted if
    layers 1 and 2 passed. Returns a dict with each layer and each signal.
    verdicts=None and judge=None means there is no judge: layer 3 is skipped."""
    l1 = layer1(item, resp, citation_check)
    l2 = faithful_check(item, resp)
    l3 = None                                            # None = judge not run
    if l1[0] and l2[0] and (judge or verdicts is not None):
        v = judge(item, resp) if judge else verdicts.get(item["id"])
        l3 = (False, "no judge verdict") if not v else (v["verdict"] == "pass", v["reason"])

    answerable = not item["should_refuse"]
    retrieved = resp.get("retrieved") or []
    case = {"id": item["id"], "l1": l1, "l2": l2, "l3": l3,
            "faithfulness": l2[0],                          # over all cases
            "recall": None, "relevance": None, "correctness": None}
    if answerable:                                          # over answerable cases
        case["recall"] = any(is_right_passage(item, h) for h in retrieved)
        case["relevance"] = bool(retrieved) and is_right_passage(item, retrieved[0])
        no_judge = judge is None and verdicts is None
        case["correctness"] = bool(l1[0] and l2[0] and (no_judge or (l3 and l3[0])))
    return case


def why_failed(case, metric):
    """One short reason a case failed a metric, for the gate message."""
    if metric == "recall":
        return "the right passage was not retrieved"
    if metric == "relevance":
        return "the top passage was not the right one"
    for res in (case["l1"], case["l2"], case["l3"]):
        if res and not res[0]:
            return res[1]
    return "failed"


def run_version(golden, responses, verdicts, **kw):
    return [score_case(item, responses[item["id"]], verdicts, **kw) for item in golden]


def metrics(cases):
    """{metric: {"rate", "passed", "total", "failing": [ids]}} for the four signals."""
    out = {}
    for key, _ in METRICS:
        scored = [c for c in cases if c[key] is not None]
        failing = [c["id"] for c in scored if not c[key]]
        n = len(scored)
        out[key] = {"rate": (n - len(failing)) / n if n else 0.0,
                    "passed": n - len(failing), "total": n, "failing": failing}
    return out


def average(m):
    return sum(m[k]["rate"] for k, _ in METRICS) / len(METRICS)


# --- the gate ---------------------------------------------------------------
def gate(candidate, baseline=None, minimum=None, tolerance=None):
    """Per-metric gate. Returns a list of problems; empty means SHIP."""
    minimum = MINIMUM if minimum is None else minimum
    tolerance = TOLERANCE if tolerance is None else tolerance
    problems = []
    for key, name in METRICS:
        now = candidate[key]["rate"]
        before = baseline[key]["rate"] if baseline else None
        below = now < minimum[key]
        regressed = before is not None and now < before - tolerance
        if below or regressed:
            new = [i for i in candidate[key]["failing"]
                   if not baseline or i not in baseline[key]["failing"]]
            problems.append({"metric": key, "name": name, "before": before, "now": now,
                             "below": below, "regressed": regressed,
                             "cases": new or candidate[key]["failing"]})
    return problems


def average_gate(candidate, baseline=None, tolerance=None):
    """The tempting shortcut: gate on one number, the mean of the four.
    Kept here only to show what it misses."""
    tolerance = TOLERANCE if tolerance is None else tolerance
    floor = sum(MINIMUM.values()) / len(MINIMUM)
    now = average(candidate)
    if now < floor:
        return False
    return baseline is None or now >= average(baseline) - tolerance


def headline(problem, cases_by_id):
    """e.g. 'faithfulness 94% → 89% (case q17: answered a question it should refuse)'"""
    p = problem
    if p["regressed"]:
        head = f"{p['name']} {p['before']:.0%} → {p['now']:.0%}"
    else:
        head = f"{p['name']} {p['now']:.0%}, below the {MINIMUM[p['metric']]:.0%} minimum"
    reasons = [f"{i}: {why_failed(cases_by_id[i], p['metric'])}" for i in p["cases"]]
    word = "case" if len(reasons) == 1 else "cases"
    return f"{head} ({word} {'; '.join(reasons)})"


# --- --live: produce the same records by running ask-the-docs for real -----
def run_live(golden, version):
    sys.path.insert(0, os.path.abspath(ASK_DIR))
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        raise SystemExit("--live runs the real ask-the-docs retrieval and needs sentence-transformers:\n"
                         "  ./setup.sh --live     (or: pip install -r ../ask-the-docs/requirements.txt)\n"
                         "Without --live the harness uses the recorded responses.")
    import ask
    retrieve = ask._retriever(ask.load_chunks())
    phrase = ask.phrase_with_model if os.environ.get("LLM_API_KEY") else None
    out = {}
    for item in golden:
        hits = retrieve(item["question"])[:3]
        r = ask.answer_question(item["question"], lambda _q: hits,
                                threshold=VERSIONS[version], phrase=phrase)
        out[item["id"]] = {
            "id": item["id"], "version": version, "threshold": VERSIONS[version],
            "retrieved": [{"passage": p, "source": s, "score": round(sc, 2)} for p, s, sc in hits],
            "answer": r.get("answer") or r.get("message"),
            "source": r.get("source"), "refused": r["refused"]}
    return out


# --- presentation (same look as the other demos) ----------------------------
def _c(code, s):
    """ANSI colour, unless output is piped or NO_COLOR is set."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def banner():
    rule = _c("2", "─" * 60)
    print(rule)
    print("  " + _c("1;38;5;44", "Leapfrog Labs") + _c("2", " · ") + _c("1", "Eval harness"))
    print("  " + _c("2", "How do you know it's working? Score it, gate it, check the judge."))
    print("  " + _c("38;5;99", "https://leapfrog.lerias.org"))
    print(rule)


STEP = "1;38;5;44"


def step(label, text):
    print("\n" + _c(STEP, label) + "  " + _c("1", text))


def note(text):
    if text.startswith("\n"):
        print()
    for line in text.strip("\n").splitlines():
        print("  " + _c("2", line))


def mark(ok):
    if ok is None:
        return _c("2", "·")
    return _c("32", "✓") if ok else _c("31", "✗")


def pct(x):
    return f"{x:.0%}"


def show_golden(golden):
    step("① GOLDEN SET", f"{len(golden)} questions with known-good criteria (golden.jsonl)")
    note("A golden set is a curated set of representative inputs with known-good\n"
         "criteria — your standing yardstick (Ch 8 & 9). Each item says which handbook\n"
         "file should be cited, which facts the answer must contain, and whether the\n"
         "system should refuse because the handbook doesn't cover it.")
    refuse = [g for g in golden if g["should_refuse"]]
    srcs = sorted({g["expected_source"] for g in golden if g["expected_source"]})
    print(f"\n  {len(golden) - len(refuse)} answerable, from {', '.join(srcs)}")
    print(f"  {len(refuse)} it should refuse:")
    for g in refuse:
        print(f"      {g['id']}  {g['question']}")


def show_runs(golden, runs, mode):
    step("② RUN TWO VERSIONS", "the same golden questions through each version")
    note("v1 is what runs today. v2 is the teammate's \"harmless\" change: a lower\n"
         "refusal threshold, so it answers more. Each response records the whole\n"
         "response path (Ch 8), not just the answer: what was retrieved, with scores,\n"
         "the answer, the cited source, and whether it refused.")
    print(f"\n  responses: {mode}")
    for v, resp in runs.items():
        answered = sum(1 for g in golden if not resp[g["id"]]["refused"])
        refused = [g["id"] for g in golden if resp[g["id"]]["refused"]]
        print(f"  {v}  threshold {VERSIONS.get(v, '?'):>5}   answered {answered:>2}   "
              f"refused {len(refused)}  ({', '.join(refused)})")
    if "v2" in runs and "v1" in runs:
        extra = [g["id"] for g in golden
                 if runs["v1"][g["id"]]["refused"] and not runs["v2"][g["id"]]["refused"]]
        if extra:
            note(f"\nv2 answers {len(extra)} more: {', '.join(extra)}. On a dashboard that counts answered\n"
                 "questions, v2 already looks better. Watch what the layers say about each.")
            r = runs["v2"][extra[-1]]
            print("\n  " + _c("2", f"one recorded response path — v2, {r['id']}:"))
            print("  " + _c("2", "  retrieved:"))
            for h in r["retrieved"]:
                print("  " + _c("2", f"    {h['score']:>5}  [{h['source']}] {h['passage']}"))
            print("  " + _c("2", f"  answer:    {r['answer']}"))
            print("  " + _c("2", f"  source:    {r['source']}   refused: {r['refused']}"))


def show_scores(golden, scored, brief=False):
    step("③ SCORE IN LAYERS", "cheap and free first, the judge last")
    if not brief:
        note("L1 programmatic  refused exactly when it should? cited? the right file?\n"
             "L2 grounded      are the key facts in the passage it used AND in the answer?\n"
             "L3 judge         a model scores against rubric.md — only if L1 and L2 passed\n"
             "                 (fail fast and cheap; spend the expensive gate last, Ch 8)\n"
             "✓ pass   ✗ fail   · not run")
        versions = list(scored)
        print("\n  " + _c("2", f"{'case':<5} {'question':<42}" + "".join(f"  {v} L1 L2 L3" for v in versions)))
        for i, g in enumerate(golden):
            q = g["question"] if len(g["question"]) <= 42 else g["question"][:39] + "..."
            cols = ""
            for v in versions:
                c = scored[v][i]
                cols += f"      {mark(c['l1'][0])}  {mark(c['l2'][0])}  {mark(c['l3'][0] if c['l3'] else None)}"
            print(f"  {g['id']:<5} {q:<42}{cols}")
        print("\n  " + _c("2", "what failed, and why (the first layer that failed):"))
        for v in versions:
            for c in scored[v]:
                for layer, res in (("L1", c["l1"]), ("L2", c["l2"]), ("L3", c["l3"])):
                    if res and not res[0]:
                        print(f"  {v}  {c['id']}  {layer}  " + _c("31", res[1]))
                        break
    print("\n  " + _c("2", "the four signals from Chapter 7:"))
    print("  " + _c("2", f"{'':<20}" + "".join(f"{v:>14}" for v in scored)))
    ms = {v: metrics(c) for v, c in scored.items()}
    for key, name in METRICS:
        row = "".join(f"{pct(ms[v][key]['rate']):>6} ({ms[v][key]['passed']:>2}/{ms[v][key]['total']:>2})"
                      for v in scored)
        print(f"  {name:<20}{row}")
    if not brief:
        note("\nrecall + relevance: over the 16 answerable questions. faithfulness: over all\n"
             "18 — a refusal claims nothing, so it is faithful; an answer to a question it\n"
             "should refuse is not. correctness: answerable questions that passed L1, L2 and L3.")
    return ms


def show_gate(ms, base_v, cand_v, scored, brief=False):
    step("④ COMPARE & GATE", f"{cand_v} vs {base_v}, metric by metric" if base_v
         else f"{cand_v} against the minimums")
    if not brief:
        note(f"BLOCKED if any metric is below its minimum, or fell by more than "
             f"{TOLERANCE * 100:.0f} points.")
    cand, base = ms[cand_v], (ms[base_v] if base_v else None)
    print()
    if base:
        print("  " + _c("2", f"{'metric':<20}{base_v:>7}{cand_v:>7}{'Δ pts':>8}{'min':>7}"))
    else:
        print("  " + _c("2", f"{'metric':<20}{cand_v:>7}{'min':>7}"))
    problems = gate(cand, base)
    bad = {p["metric"] for p in problems}
    for key, name in METRICS:
        ok = mark(key not in bad)
        if base:
            d = (cand[key]["rate"] - base[key]["rate"]) * 100
            print(f"  {name:<20}{pct(base[key]['rate']):>7}{pct(cand[key]['rate']):>7}"
                  f"{d:>+8.1f}{pct(MINIMUM[key]):>7}  {ok}")
        else:
            print(f"  {name:<20}{pct(cand[key]['rate']):>7}{pct(MINIMUM[key]):>7}  {ok}")
    if base and not brief:
        avg_ship = average_gate(cand, base)
        hides = avg_ship and bool(problems)
        print("  " + _c("2", f"{'average of the four':<20}{average(base):>7.1%}{average(cand):>7.1%}"
                             f"{(average(cand) - average(base)) * 100:>+8.1f}"))
        if hides:
            note(f"\nA gate on the average alone would SHIP {cand_v}: the gain in one metric hides\n"
                 "the loss in another. That is why this gate checks each metric on its own.")

    by_id = {c["id"]: c for c in scored[cand_v]}
    print("\n  " + _c("2", "─" * 58))
    if problems:
        for p in problems:
            print("  " + _c("1;31", "BLOCKED — ") + _c("31", headline(p, by_id)))
        if not brief and base and any(p["metric"] == "faithfulness" for p in problems):
            note(f"\n{cand_v} may answer more, and score better elsewhere. It still doesn't ship:\n"
                 "a gate checks every metric, and one of them got worse.")
        return 1
    print("  " + _c("1;32", "SHIP") + _c("32", f" — {cand_v} clears every metric"
                                              + (f" and does not regress against {base_v}." if base else ".")))
    return 0


def _wrapped(label, text, first=0, width=78, indent=14):
    """Wrap long text under a label, so lines don't break mid-word."""
    lines = textwrap.wrap(text, width=width - indent - first) or [""]
    rest = textwrap.wrap(" ".join(lines[1:]), width=width - indent) if len(lines) > 1 else []
    return label + "\n".join([lines[0]] + [" " * indent + r for r in rest])


def show_calibration(golden, version, verdicts, humans):
    step("⑤ CHECK THE JUDGE", f"judge verdicts vs human labels, {version} ({len(humans)} cases)")
    note("An LLM judge has blind spots of its own. So before you trust it, you align it\n"
         "against human ratings on a sample (Ch 9). humans.jsonl is that sample.")
    by_q = {g["id"]: g for g in golden}
    resp = load_responses(version)
    agree, diffs = 0, []
    for cid, h in humans.items():
        j = verdicts.get(cid)
        if j and j["verdict"] == h["label"]:
            agree += 1
        else:
            diffs.append((cid, j, h))
    n = len(humans)
    print(f"\n  agreement: {_c('1', f'{agree}/{n} = {agree / n:.0%}')}")
    if diffs:
        print("\n  " + _c("2", "where the judge and the human disagree:"))
    for cid, j, h in diffs:
        jv = j["verdict"] if j else "none"
        print(f"\n  {_c('1', cid)}  {by_q[cid]['question']}")
        print(_wrapped("      answer: ", resp[cid]["answer"]))
        print("      judge:  " + _c("32" if jv == "pass" else "31", jv.upper())
              + _c("2", _wrapped("", f" — {j['reason'] if j else ''}", first=len(jv))))
        print("      human:  " + _c("32" if h["label"] == "pass" else "31", h["label"].upper())
              + _c("2", _wrapped("", f" — {h['note']}", first=len(h["label"]))))
        if jv == "pass" and h["label"] == "fail":
            print("      " + _c("33", "⚠ fluent but wrong: the judge passed it, a person failed it."))
        elif jv == "fail" and h["label"] == "pass":
            print("      " + _c("33", "⚠ too strict: the judge failed a right answer."))
    print("\n  " + _c("2", "─" * 58))
    note("The harness's correctness score leans on this judge. Read the disagreements,\n"
         "fix the rubric or the judge, and calibrate again.")
    print("  " + _c("1", "A judge you haven't checked against people is not a measurement;"))
    print("  " + _c("1", "it's a guess with a decimal point.") + _c("2", "  (Ch 9)"))
    return 0


# --- driver -----------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Leapfrog eval harness — score it, gate it, check the judge")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--offline", action="store_true", help="use the recorded responses (default)")
    src.add_argument("--live", action="store_true",
                     help="run ask-the-docs for real (needs sentence-transformers)")
    ap.add_argument("--judge", action="store_true",
                    help="layer 3: ask a local model with rubric.md instead of the recorded verdicts")
    ap.add_argument("--nli", action="store_true",
                    help="layer 2: add an entailment model (needs sentence-transformers)")
    ap.add_argument("--calibrate", action="store_true", help="check the judge against human labels")
    ap.add_argument("--brief", action="store_true", help="just the scores and the verdict")
    ap.add_argument("--version", choices=["v1", "v2", "both"], default="both",
                    help="which version to gate (both = v2 against v1 as the baseline)")
    args = ap.parse_args(argv)

    banner()
    golden = load_golden()

    if args.calibrate:
        version = "v2" if args.version == "both" else args.version
        if args.judge:
            resp = load_responses(version)
            verdicts = {g["id"]: judge_live(g, resp[g["id"]]) for g in golden}
        else:
            verdicts = load_judge(version)
        humans = {k: v for k, v in load_humans().items() if v.get("version", version) == version}
        if not humans:
            print(f"  no human labels for {version} in humans.jsonl")
            return 2
        return show_calibration(golden, version, verdicts, humans)

    versions = ["v1", "v2"] if args.version == "both" else [args.version]
    if args.live:
        mode = "LIVE — ask-the-docs retrieval" + (", phrased by " + MODEL
                                                  if os.environ.get("LLM_API_KEY") else "")
        runs = {v: run_live(golden, v) for v in versions}
    else:
        mode = "OFFLINE — recorded in responses/ (synthetic, for this demo)"
        runs = {v: load_responses(v) for v in versions}

    kw = {}
    if args.nli:
        kw["faithful_check"] = nli_faithful_check()
    if args.judge:
        kw["judge"] = judge_live
    # Recorded verdicts only match the recorded responses. A live run gets a
    # live judge (--judge) or no layer 3 at all.
    scored = {v: run_version(golden, runs[v], None if args.live else load_judge(v), **kw)
              for v in versions}
    if args.live and not args.judge:
        note("\nlayer 3 skipped: the recorded judge verdicts only match the recorded\n"
             "responses. Add --judge to score live answers with a local model.")

    if not args.brief:
        show_golden(golden)
        show_runs(golden, runs, mode)
    ms = show_scores(golden, scored, brief=args.brief)
    base_v, cand_v = (versions[0], versions[1]) if len(versions) == 2 else (None, versions[0])
    code = show_gate(ms, base_v, cand_v, scored, brief=args.brief)
    if not args.brief:
        note("\nnext: --calibrate checks the judge these numbers lean on.")
    return code


if __name__ == "__main__":
    sys.exit(main())
