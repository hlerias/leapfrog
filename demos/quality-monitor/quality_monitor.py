# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Quality monitor — alert on quality, not latency               Ch 9
# No API key, no install — runs as-is on a recorded week of traces.
#
# WHAT IT IS    Production monitoring for the ask-the-docs demo. A week of
#               traffic where the dashboard stays green and, from day 4,
#               travel answers quietly go wrong. Nothing you were watching
#               was built to see it. This is what is.
# HOW IT WORKS  1) the old dashboard: requests, latency, errors per day
#               2) sample the traffic and score it with the eval harness's
#                  cheap scorers; write the score back onto the span
#               3) quality per day, overall and per segment
#               4) alert on a quality drop per segment
#               5) root cause by elimination, walking the trace
#               6) --guard: replay with a runtime guardrail
# PROOF POINT   Latency, errors and the overall score barely move. The travel
#               segment falls from day 4, the per-segment alert fires, an
#               alert on the global average or on latency never does, and the
#               trace points at the index, not the model.
# WHY DO IT     "Alert on quality, not just on latency" (Ch 9). A serious
#               problem in one workflow drowns in an average across all of them.
#
# Run:  python demos/quality-monitor/quality_monitor.py
#       python demos/quality-monitor/quality_monitor.py --guard     (adds step 6)
#       python demos/quality-monitor/quality_monitor.py --day 4     (one day's traces)

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRACES = os.path.join(HERE, "traces", "week.jsonl")

# The scorers come from the eval harness (Demo A): the same checks that gate a
# change before it ships now watch it after it ships. Nothing is duplicated.
sys.path.insert(0, os.path.join(HERE, "..", "eval-harness"))
import eval_harness as eh  # noqa: E402

# --- config (env vars override) ---------------------------------------------
SAMPLE_RATE = float(os.environ.get("QM_SAMPLE_RATE", "0.5"))       # share of traffic scored
ALERT_THRESHOLD = float(os.environ.get("QM_ALERT_THRESHOLD", "0.85"))  # faithfulness floor
ALERT_WINDOW = int(os.environ.get("QM_ALERT_WINDOW", "1"))          # days averaged per check
MIN_SAMPLES = int(os.environ.get("QM_MIN_SAMPLES", "5"))            # don't alert on fewer
P99_LIMIT_MS = float(os.environ.get("QM_P99_MS", "3000"))           # the old latency alert
ERROR_LIMIT = float(os.environ.get("QM_MAX_ERROR_RATE", "0.02"))    # the old error alert

SEGMENTS = ["travel", "expenses", "oncall", "offsites"]
REFUSAL = "I couldn't find that in the handbook."


# --- reading traces -----------------------------------------------------------
def load_traces(path=TRACES):
    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    return [r for r in rows if "_note" not in r]


def span(trace, name):
    return next(s for s in trace["spans"] if s["name"] == name)


def attr(trace, name, key, default=None):
    return span(trace, name)["attributes"].get(key, default)


def segment(trace):
    return attr(trace, "request", "app.segment")


def days(traces):
    return sorted({t["day"] for t in traces})


def to_response(trace):
    """The trace, in the response shape the eval harness scores. None if the call errored."""
    gen = span(trace, "generation")["attributes"]
    if gen.get("error"):
        return None
    return {"answer": gen["output.answer"], "source": gen["output.source"],
            "refused": gen["output.refused"],
            "retrieved": attr(trace, "retrieval", "retrieval.documents") or []}


# --- ① the old dashboard -------------------------------------------------------
def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))] if values else 0


def dashboard(traces):
    out = {}
    for d in days(traces):
        today = [t for t in traces if t["day"] == d]
        lat = [attr(t, "request", "latency_ms") for t in today]
        errors = sum(1 for t in today if attr(t, "request", "error"))
        out[d] = {"requests": len(today), "p50": percentile(lat, 0.50), "p99": percentile(lat, 0.99),
                  "error_rate": errors / len(today), "date": today[0]["timestamp"][:10]}
    return out


# --- ② sample and score --------------------------------------------------------
def sampled(trace, rate=None):
    """Head sampling on the trace id: the same trace is always in or out."""
    rate = SAMPLE_RATE if rate is None else rate
    return int(trace["trace_id"][:8], 16) / 2 ** 32 < rate


def score_trace(trace):
    """Layer 1 (cited?) and layer 2 (grounded?) from the eval harness, then the
    score is written back onto the generation span, as Chapter 9 describes."""
    resp = to_response(trace)
    if resp is None:
        return None
    cited, why_c = eh.check_citation({"expected_source": None}, resp)
    grounded, why_g = eh.check_grounded(resp)
    ok = cited and grounded
    gen = span(trace, "generation")["attributes"]
    gen["eval.cited"] = cited
    gen["eval.faithfulness"] = 1.0 if ok else 0.0
    gen["eval.reason"] = why_g if cited else why_c
    return gen["eval.faithfulness"]


def score_sample(traces, rate=None):
    scored = []
    for t in traces:
        if sampled(t, rate) and score_trace(t) is not None:
            scored.append(t)
    return scored


# --- ③ quality per day, overall and per segment -----------------------------
def daily_quality(scored):
    """{"all" | segment: {day: (passed, total)}}"""
    table = {k: {} for k in ["all"] + SEGMENTS}
    for t in scored:
        f = attr(t, "generation", "eval.faithfulness")
        for key in ("all", segment(t)):
            p, n = table[key].get(t["day"], (0, 0))
            table[key][t["day"]] = (p + f, n + 1)
    return table


def rate(cell):
    return cell[0] / cell[1] if cell and cell[1] else None


# --- ④ alerts ------------------------------------------------------------------
def quality_alerts(table, keys, threshold=None, window=None, min_samples=None):
    """Fire when faithfulness over the last `window` days falls below the threshold."""
    threshold = ALERT_THRESHOLD if threshold is None else threshold
    window = ALERT_WINDOW if window is None else window
    min_samples = MIN_SAMPLES if min_samples is None else min_samples
    fired = []
    for key in keys:
        all_days = sorted(table[key])
        for i, d in enumerate(all_days):
            cells = [table[key][x] for x in all_days[max(0, i - window + 1):i + 1]]
            p, n = sum(c[0] for c in cells), sum(c[1] for c in cells)
            if n >= min_samples and p / n < threshold:
                fired.append((key, d, p / n))
    return fired


def segment_alerts(table, **kw):
    return quality_alerts(table, SEGMENTS, **kw)


def global_alerts(table, **kw):
    return quality_alerts(table, ["all"], **kw)


def latency_alerts(dash):
    return [(d, v["p99"]) for d, v in dash.items() if v["p99"] > P99_LIMIT_MS]


def error_alerts(dash):
    return [(d, v["error_rate"]) for d, v in dash.items() if v["error_rate"] > ERROR_LIMIT]


# --- ⑤ root cause by elimination ----------------------------------------------
def tool_spans(trace):
    return sum(1 for s in trace["spans"] if s["name"].startswith("tool"))


COMPONENTS = [   # Chapter 9's walk down the tree, with the model first: that's the bet
    ("model", "gen_ai.request.model", lambda t: attr(t, "generation", "gen_ai.request.model")),
    ("prompt", "app.prompt_version", lambda t: attr(t, "generation", "app.prompt_version")),
    ("tools", "tool spans", lambda t: tool_spans(t) or "none"),
    ("router", "app.route", lambda t: attr(t, "request", "app.route")),
    ("retrieval", "app.index_version", lambda t: attr(t, "retrieval", "app.index_version")),
]


def root_cause(scored, seg, from_day):
    """Compare the failing traces of `seg` from `from_day` with that segment's
    traces before it, one component of the response path at a time."""
    before = [t for t in scored if segment(t) == seg and t["day"] < from_day]
    after = [t for t in scored if segment(t) == seg and t["day"] >= from_day
             and attr(t, "generation", "eval.faithfulness") == 0.0]
    rows = []
    for name, key, get in COMPONENTS:
        b, a = sorted({str(get(t)) for t in before}), sorted({str(get(t)) for t in after})
        rows.append({"component": name, "attribute": key, "before": b, "after": a, "changed": b != a})
    return rows, before, after


def top_score(trace):
    docs = attr(trace, "retrieval", "retrieval.documents") or []
    return docs[0]["score"] if docs else None


def evidence(before, after):
    """For each failing question: what it retrieved before, and what it retrieves now."""
    out = []
    for q in sorted({attr(t, "request", "input.question") for t in after}):
        was = [t for t in before if attr(t, "request", "input.question") == q]
        now = [t for t in after if attr(t, "request", "input.question") == q]
        if was and now:
            out.append((q, attr(was[0], "retrieval", "retrieval.documents")[0],
                        attr(now[0], "retrieval", "retrieval.documents")[0]))
    return out


# --- ⑥ the runtime guardrail ----------------------------------------------------
def guard(resp):
    """Before the user sees it: an answer that is uncited or not grounded in its
    passage becomes an honest refusal. Returns (response, stopped, reason)."""
    if resp["refused"]:
        return resp, False, ""
    cited, why_c = eh.check_citation({"expected_source": None}, resp)
    grounded, why_g = eh.check_grounded(resp)
    if cited and grounded:
        return resp, False, ""
    safe = dict(resp, answer=REFUSAL, source=None, refused=True)
    return safe, True, why_g if cited else why_c


def replay_with_guard(traces, guard_fn=guard):
    """Run every response of the week (not just the sample) through the guardrail."""
    stopped = []
    for t in traces:
        resp = to_response(t)
        if resp is None:
            continue
        _, was_stopped, why = guard_fn(resp)
        if was_stopped:
            stopped.append((t, why))
    return stopped


# --- presentation ---------------------------------------------------------------
def _c(code, s):
    """ANSI colour, unless output is piped or NO_COLOR is set."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def banner():
    rule = _c("2", "─" * 60)
    print(rule)
    print("  " + _c("1;38;5;44", "Leapfrog Labs") + _c("2", " · ") + _c("1", "Quality monitor"))
    print("  " + _c("2", "Alert on quality, not latency."))
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


def ok_mark(ok):
    return _c("32", "✓") if ok else _c("31", "✗")


def show_dashboard(dash, brief=False):
    step("① THE OLD DASHBOARD", "requests, latency and errors, per day")
    if not brief:
        note("Chapter 9 opens here: \"You open the dashboard: traffic healthy, latency fine,\n"
             "no errors.\" This is that dashboard, for one week of ask-the-docs traffic.")
    print("\n  " + _c("2", f"{'day':<4}{'date':<12}{'requests':>9}{'p50 ms':>9}{'p99 ms':>9}{'errors':>9}"))
    for d, v in dash.items():
        healthy = v["p99"] <= P99_LIMIT_MS and v["error_rate"] <= ERROR_LIMIT
        print(f"  {d:<4}{v['date']:<12}{v['requests']:>9}{v['p50']:>9}{v['p99']:>9}"
              f"{v['error_rate']:>9.1%}  {ok_mark(healthy)}")
    print("  " + _c("32", "All green.") + _c("2", f" (alerts: p99 over {P99_LIMIT_MS:.0f} ms, "
                                                  f"errors over {ERROR_LIMIT:.0%})"))


def show_trace(t, label):
    req, ret, gen = (span(t, n)["attributes"] for n in ("request", "retrieval", "generation"))
    top = ret["retrieval.documents"][0]
    print("  " + _c("2", label))
    print(f"  trace {t['trace_id'][:8]} · {t['timestamp'][:16].replace('T', ' ')} · {req['app.segment']}")
    print(f"  └ request     {req['latency_ms']} ms   \"{req['input.question']}\"")
    print(f"    ├ retrieval  {ret['app.index_version']}   top: [{top['source']}] {top['score']}")
    print(f"    │            \"{top['passage']}\"")
    print(f"    └ generation {gen['gen_ai.request.model']} · {gen['app.prompt_version']} · "
          f"{gen['gen_ai.usage.input_tokens']}→{gen['gen_ai.usage.output_tokens']} tokens")
    print(f"                 \"{gen['output.answer']}\"")
    f = gen["eval.faithfulness"]
    print("                 " + _c("1;31" if f == 0 else "1;32", f"eval.faithfulness = {f}")
          + _c("2", f"  ← written back onto the span ({gen['eval.reason']})"))


def show_scoring(traces, scored, brief=False):
    step("② SAMPLE & SCORE", "the eval harness's cheap scorers, on live traffic")
    if not brief:
        note("Real volume dwarfs any test set, so you lean on cheaper scorers and sampling\n"
             "(Ch 9). Each sampled trace gets layer 1 (did it cite a source?) and layer 2\n"
             "(are the numbers and names it states in the passage it used?), imported from\n"
             "../eval-harness. The score is written back onto the generation span.")
    n_ok = sum(1 for t in traces if to_response(t) is not None)
    print(f"\n  scored {len(scored)} of {n_ok} answers (sample rate {SAMPLE_RATE:.0%}, "
          f"by trace id)")
    if not brief:
        bad = [t for t in scored if attr(t, "generation", "eval.faithfulness") == 0.0
               and segment(t) == "travel"]
        if bad:
            print()
            show_trace(bad[0], "one scored trace tree, as stored:")


def show_quality(table, brief=False):
    step("③ BY SEGMENT", "daily faithfulness, overall and per segment")
    if not brief:
        note("Same scores, two ways of adding them up: one number for all traffic, and one\n"
             "per segment of the handbook.")
    ds = sorted(table["all"])
    print("\n  " + _c("2", f"{'':<10}" + "".join(f"{'day ' + str(d):>8}" for d in ds)))
    for key in ["all"] + SEGMENTS:
        cells = ""
        for d in ds:
            r = rate(table[key].get(d))
            txt = f"{r:>8.0%}" if r is not None else f"{'—':>8}"
            cells += _c("31", txt) if (r is not None and r < ALERT_THRESHOLD) else txt
        label = f"{'overall' if key == 'all' else key:<10}"
        print("  " + (_c("1", label) if key == "all" else label) + cells)
    if not brief:
        lo = min(rate(table["all"][d]) for d in ds)
        note(f"\nThe overall line never drops below {lo:.0%}. Travel falls from day 4. A serious\n"
             "problem in one workflow drowns unnoticed in an average across all of them (Ch 9).")


def show_alerts(table, dash, brief=False):
    step("④ ALERT", f"faithfulness below {ALERT_THRESHOLD:.0%} over {ALERT_WINDOW} day(s)")
    seg = segment_alerts(table)
    glob = global_alerts(table)
    lat, err = latency_alerts(dash), error_alerts(dash)
    print()
    for key, d, r in seg:
        print("  " + _c("1;31", "ALERT") + f"  {key:<9} day {d}  faithfulness {r:.0%}")
    if not seg:
        print("  " + _c("2", "no segment alert"))
    print("\n  " + _c("2", "the same week, through other alert rules:"))
    lo = min(rate(c) for c in table["all"].values())
    print(f"  {ok_mark(not glob)} {'same rule on the global average':<36}"
          + (_c("31", f"fires {len(glob)}x") if glob else f"never fires (lowest day {lo:.0%})"))
    hi = max(v["p99"] for v in dash.values())
    print(f"  {ok_mark(not lat)} {'p99 latency over ' + format(P99_LIMIT_MS, '.0f') + ' ms':<36}"
          + (_c("31", f"fires {len(lat)}x") if lat else f"never fires (highest p99 {hi} ms)"))
    he = max(v["error_rate"] for v in dash.values())
    print(f"  {ok_mark(not err)} {'error rate over ' + format(ERROR_LIMIT, '.0%'):<36}"
          + (_c("31", f"fires {len(err)}x") if err else f"never fires (highest {he:.1%})"))
    if not brief and seg:
        note("\n✓ here means \"stayed quiet\" — which is exactly the problem. Only the rule\n"
             "that watches quality per segment sees it.")
    return seg


def show_root_cause(scored, seg, from_day, brief=False):
    step("⑤ ROOT CAUSE BY ELIMINATION", f"{seg}: failing traces from day {from_day} vs before")
    rows, before, after = root_cause(scored, seg, from_day)
    if not brief:
        note("Walk the response path, one component at a time (Ch 9). Bet, before you look,\n"
             "that it's the model — and notice how often it isn't.")
    print("\n  " + _c("2", f"{'component':<11}{'attribute':<22}{'before':<20}{'failing now':<20}"))
    for r in rows:
        b, a = ", ".join(r["before"]), ", ".join(r["after"])
        verdict = _c("1;31", "CHANGED") if r["changed"] else _c("2", "same")
        print(f"  {r['component']:<11}{r['attribute']:<22}{b:<20}{a:<20}{verdict}")
    changed = [r for r in rows if r["changed"]]
    if not brief:
        print("\n  " + _c("2", "what those questions retrieved, before and now:"))
        for q, was, now in evidence(before, after):
            print(f"  \"{q}\"")
            print("    " + _c("2", f"before  {was['score']:>5}  ") + was["passage"])
            print("    " + _c("2", f"now     {now['score']:>5}  ") + _c("31", now["passage"]))
    print()
    if changed:
        r = changed[0]
        print("  " + _c("1", f"It isn't the model. It's {r['component']}: {r['attribute']} "
                             f"{', '.join(r['before'])} → {', '.join(r['after'])}."))
        if not brief:
            note("The rebuilt index no longer finds the passages these questions need, and the\n"
                 "model answers anyway, from whatever it was handed (Ch 7). Latency, errors and\n"
                 "the model never moved. Next: check what the day-4 rebuild indexed for travel.")
    return changed


def show_guard(traces, brief=False):
    step("⑥ GUARDRAIL", "replay the week with a runtime check before the user sees it")
    if not brief:
        note("A runtime guardrail inspects the output before it reaches the user (Ch 9). This\n"
             "one runs the same two checks on EVERY response, not a sample: an answer that is\n"
             "uncited or not grounded in its passage becomes an honest refusal.")
    stopped = replay_with_guard(traces)
    by = {}
    for t, _ in stopped:
        key = (segment(t), "from day 4" if t["day"] >= 4 else "days 1–3")
        by[key] = by.get(key, 0) + 1
    total = sum(1 for t in traces if to_response(t) is not None)
    print(f"\n  stopped {_c('1', str(len(stopped)))} of {total} answers before they reached a user")
    for (seg, when), n in sorted(by.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"    {seg:<9} {when:<11} {n:>3}")
    ex = next((t for t, _ in stopped if segment(t) == "travel"), None)
    if ex and not brief:
        resp = to_response(ex)
        print("\n  " + _c("2", "for example:"))
        print(f"  \"{attr(ex, 'request', 'input.question')}\"")
        print("    " + _c("2", "would have said  ") + _c("31", resp["answer"]))
        print("    " + _c("2", "now says         ") + _c("32", REFUSAL))
        note("\nAn honest \"I don't know\" instead of a confident fabrication (Ch 7). The guardrail\n"
             "is the safety net, not the fix: the fix is the index.")
    return stopped


def show_day(traces, d):
    step(f"DAY {d}", "every trace, as recorded")
    today = [t for t in traces if t["day"] == d]
    if not today:
        print(f"  no traces for day {d}")
        return 2
    print("  " + _c("2", f"{'time':<6}{'segment':<10}{'ms':>6}  {'index':<15}{'top':>6}  {'faithful':<9}question"))
    for t in today:
        f = score_trace(t)
        mark = _c("2", "error") if f is None else (ok_mark(f == 1.0) + "        ")
        q = attr(t, "request", "input.question")
        print(f"  {t['timestamp'][11:16]:<6}{segment(t):<10}{attr(t, 'request', 'latency_ms'):>6}  "
              f"{attr(t, 'retrieval', 'app.index_version'):<15}{str(top_score(t)):>6}  {mark} {q}")
    return 0


# --- driver -----------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Leapfrog quality monitor — alert on quality, not latency")
    ap.add_argument("--guard", action="store_true", help="replay the week with a runtime guardrail")
    ap.add_argument("--day", type=int, help="show one day's traces and exit")
    ap.add_argument("--brief", action="store_true", help="the tables and the verdicts only")
    args = ap.parse_args(argv)

    banner()
    traces = load_traces()
    if args.day:
        return show_day(traces, args.day)

    dash = dashboard(traces)
    show_dashboard(dash, args.brief)
    scored = score_sample(traces)
    show_scoring(traces, scored, args.brief)
    table = daily_quality(scored)
    show_quality(table, args.brief)
    fired = show_alerts(table, dash, args.brief)
    if fired:
        seg, first_day = fired[0][0], min(d for k, d, _ in fired if k == fired[0][0])
        show_root_cause(scored, seg, first_day, args.brief)
    if args.guard:
        show_guard(traces, args.brief)
    elif not args.brief:
        note("\nnext: --guard replays the week with a runtime guardrail; --day 4 shows that day's traces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
