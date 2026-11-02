# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# Tests for the quality monitor — no model, no network, standard library only.
#   1. the data: regenerates byte for byte, uses only real handbook passages,
#      and has the scenario the brief asks for (index changes on day 4; prompt
#      and model never do)
#   2. the monitor: dashboard all green, scores come from the eval harness and
#      are written back onto spans, travel alert fires on day 4, global /
#      latency / error alerts don't, root cause names the index, guard stops
#      the stale answers
#   3. both exercises: stub → BLOCKED, spoiler → SHIP
#
# Run:  python demos/quality-monitor/test_monitor.py

import contextlib
import importlib.util
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_traces  # noqa: E402
import quality_monitor as qm  # noqa: E402

TRACES = qm.load_traces()


def _scored():
    return qm.score_sample(qm.load_traces())


def _quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


# --- 1. the data ---------------------------------------------------------------
def test_traces_regenerate_identically():
    with tempfile.TemporaryDirectory() as tmp:
        path = make_traces.write(os.path.join(tmp, "week.jsonl"))
        assert open(path, "rb").read() == open(qm.TRACES, "rb").read(), \
            "traces/week.jsonl differs from what make_traces.py generates"
    print(f"OK — make_traces.py regenerates traces/week.jsonl byte for byte ({len(TRACES)} traces)")


def test_passages_are_real_handbook_text():
    handbook = qm.eh.handbook_files()
    for text, src in make_traces.P.values():
        assert text in handbook[src], (src, text)
    print(f"OK — all {len(make_traces.P)} passages are verbatim lines of the ask-the-docs handbook")


def test_scenario_and_attribute_names():
    t = TRACES[0]
    assert [s["name"] for s in t["spans"]] == ["request", "retrieval", "generation"]
    gen = qm.span(t, "generation")["attributes"]
    for key in ("gen_ai.request.model", "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens",
                "app.prompt_version", "latency_ms", "error"):
        assert key in gen, key
    assert "app.index_version" in qm.span(t, "retrieval")["attributes"]
    assert qm.attr(t, "request", "app.segment") in qm.SEGMENTS
    idx = {d: {qm.attr(x, "retrieval", "app.index_version") for x in TRACES if x["day"] == d}
           for d in range(1, 8)}
    assert all(len(v) == 1 for v in idx.values()), idx
    assert idx[3] != idx[4] and idx[1] == idx[3] and idx[4] == idx[7], idx
    assert len({qm.attr(x, "generation", "app.prompt_version") for x in TRACES}) == 1
    assert len({qm.attr(x, "generation", "gen_ai.request.model") for x in TRACES}) == 1
    print("OK — trace trees use the GenAI names; index changes on day 4, prompt and model never")


# --- 2. the monitor ---------------------------------------------------------------
def test_old_dashboard_all_green():
    dash = qm.dashboard(TRACES)
    assert len(dash) == 7
    assert not qm.latency_alerts(dash) and not qm.error_alerts(dash), dash
    p99s = [v["p99"] for v in dash.values()]
    assert max(p99s) < 2 * min(p99s), p99s          # flat, not just under the limit
    print(f"OK — old dashboard all green: p99 {min(p99s)}–{max(p99s)} ms, errors under 2% every day")


def test_scores_come_from_the_eval_harness_and_go_onto_the_span():
    assert os.path.samefile(qm.eh.__file__, os.path.join(HERE, "..", "eval-harness", "eval_harness.py"))
    t = next(x for x in qm.load_traces() if qm.to_response(x))
    f = qm.score_trace(t)
    gen = qm.span(t, "generation")["attributes"]
    assert gen["eval.faithfulness"] == f and "eval.reason" in gen
    ok, _ = qm.eh.check_grounded(qm.to_response(t))
    assert (f == 1.0) == (ok and gen["eval.cited"])
    print("OK — scores come from ../eval-harness and are written back as eval.faithfulness")


def test_travel_alert_fires_on_day_4_and_nothing_else_does():
    table = qm.daily_quality(_scored())
    seg = qm.segment_alerts(table)
    assert {k for k, _, _ in seg} == {"travel"}, seg
    assert min(d for _, d, _ in seg) == 4 and {d for _, d, _ in seg} == {4, 5, 6, 7}, seg
    assert qm.global_alerts(table) == [], qm.global_alerts(table)
    assert all(qm.rate(table["travel"][d]) == 1.0 for d in (1, 2, 3))
    print("OK — travel alert fires on days 4–7; the global-average alert never fires")


def test_root_cause_is_the_index_not_the_model():
    rows, before, after = qm.root_cause(_scored(), "travel", 4)
    changed = [r["component"] for r in rows if r["changed"]]
    assert changed == ["retrieval"], rows
    r = next(r for r in rows if r["component"] == "retrieval")
    assert r["attribute"] == "app.index_version" and r["before"] != r["after"]
    assert before and after and qm.evidence(before, after)
    print(f"OK — root cause: model, prompt, tools, router same; index {r['before'][0]} → {r['after'][0]}")


def test_guard_stops_the_stale_answers():
    stopped = qm.replay_with_guard(TRACES)
    travel_after = [t for t, _ in stopped if qm.segment(t) == "travel" and t["day"] >= 4]
    travel_before = [t for t, _ in stopped if qm.segment(t) == "travel" and t["day"] < 4]
    assert len(travel_after) >= 30 and not travel_before, (len(travel_after), len(travel_before))
    for t in TRACES:                               # every stale travel answer is stopped
        resp = qm.to_response(t)
        if resp and qm.segment(t) == "travel" and t["day"] >= 4 and not resp["refused"]:
            if not qm.eh.check_grounded(resp)[0]:
                assert t in [x for x, _ in stopped]
    safe, was, _ = qm.guard(qm.to_response(travel_after[0]))
    assert was and safe["refused"] and safe["answer"] == qm.REFUSAL
    print(f"OK — guard stops {len(stopped)} answers, {len(travel_after)} of them stale travel from day 4")


def test_cli_runs():
    assert _quiet(qm.main, []) == 0
    assert _quiet(qm.main, ["--guard", "--brief"]) == 0
    assert _quiet(qm.main, ["--day", "4"]) == 0
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        qm.main(["--guard"])
    text = out.getvalue()
    for must in ("All green.", "ALERT  travel    day 4", "never fires", "It isn't the model",
                 "app.index_version", "notice how often it isn't", "stopped"):
        assert must in text, must
    print("OK — CLI: default, --guard --brief and --day 4 all run; the key lines are printed")


# --- 3. the exercises ----------------------------------------------------------------
def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _spoiler(name):
    src = open(os.path.join(HERE, name + ".py"), encoding="utf-8").read()
    block = src.split("SPOILER", 1)[1].split("\n", 1)[1]
    return "\n".join(line[2:] if line.startswith("# ") else line.lstrip("#")
                     for line in block.splitlines())


def test_your_turns():
    for n in (1, 2):
        name = f"your_turn_{n}"
        mod = _load(name)
        assert _quiet(mod.grade) == 1, f"{name}: the stub should be BLOCKED"
        exec(_spoiler(name), mod.__dict__)
        assert _quiet(mod.grade) == 0, f"{name}: the spoiler should SHIP"
    print("OK — your_turn_1..2: stub → BLOCKED, spoiler solution → SHIP")


if __name__ == "__main__":
    qm.banner()
    print("  " + qm._c("2", "tests · data, monitor, alerts, root cause, guardrail, exercises (no models)\n"))
    test_traces_regenerate_identically()
    test_passages_are_real_handbook_text()
    test_scenario_and_attribute_names()
    test_old_dashboard_all_green()
    test_scores_come_from_the_eval_harness_and_go_onto_the_span()
    test_travel_alert_fires_on_day_4_and_nothing_else_does()
    test_root_cause_is_the_index_not_the_model()
    test_guard_stops_the_stale_answers()
    test_cli_runs()
    test_your_turns()
    print("\n" + qm._c("32", "ALL TESTS PASSED"))
