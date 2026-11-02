# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# Tests for the eval harness — no model, no network, standard library only.
#   1. the golden set is honest: every source and fact is really in the handbook
#   2. each scoring layer does its job, and the judge only runs after L1 + L2
#   3. the proof point holds: faithfulness 94% → 89%, per-metric gate blocks v2,
#      an average-only gate would ship it, exit codes work for CI
#   4. every your_turn exercise fails with its stub and passes with its spoiler
#
# Run:  python demos/eval-harness/test_harness.py

import contextlib
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eval_harness as eh  # noqa: E402

GOLDEN = eh.load_golden()
GOLD = {g["id"]: g for g in GOLDEN}


def _scored(version):
    return eh.run_version(GOLDEN, eh.load_responses(version), eh.load_judge(version))


def _quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


# --- 1. the golden set ------------------------------------------------------
def test_golden_shape():
    assert len(GOLDEN) == 18, len(GOLDEN)
    assert len(GOLD) == 18, "ids must be unique"
    refuse = [g for g in GOLDEN if g["should_refuse"]]
    assert len(refuse) == 2, refuse
    assert any(g["question"] == "What is the company's policy on remote work?" for g in refuse)
    for g in GOLDEN:
        assert set(g) == {"id", "question", "expected_source", "must_include", "should_refuse"}, g
    print("OK — golden set: 18 items, exactly 2 to refuse (incl. the remote-work question)")


def test_golden_only_real_handbook_files_and_facts():
    files = eh.handbook_files()
    assert {"travel.txt", "expenses.txt", "oncall.txt", "offsites.txt"} <= set(files), files
    for g in GOLDEN:
        if g["should_refuse"]:
            assert g["expected_source"] is None and g["must_include"] == [], g
            continue
        assert g["expected_source"] in files, g
        for fact in g["must_include"]:
            assert fact.lower() in files[g["expected_source"]].lower(), (g["id"], fact)
    print("OK — every golden source is a real handbook file, every fact is in it")


# --- 2. the layers ----------------------------------------------------------
def test_layer1_programmatic():
    v1, v2 = eh.load_responses("v1"), eh.load_responses("v2")
    assert eh.layer1(GOLD["q01"], v2["q01"])[0] is True
    ok, why = eh.layer1(GOLD["q17"], v2["q17"])
    assert not ok and why == "answered a question it should refuse", why
    ok, why = eh.layer1(GOLD["q07"], v1["q07"])
    assert not ok and why == "refused a question the handbook answers", why
    miscited = dict(v2["q08"], source="travel.txt")
    ok, why = eh.layer1(GOLD["q08"], miscited)
    assert not ok and "expected expenses.txt" in why, why
    ok, why = eh.layer1(GOLD["q08"], dict(v2["q08"], source=None))
    assert not ok and why == "no source cited", why
    print("OK — layer 1: refusal match, citation present, citation to the right file")


def test_layer2_grounded():
    v2 = eh.load_responses("v2")
    assert eh.check_faithful(GOLD["q01"], v2["q01"])[0] is True
    ok, why = eh.check_faithful(GOLD["q06"], v2["q06"])           # 50 EUR vs 40 EUR
    assert not ok and "40 EUR" in why, why
    assert eh.check_faithful(GOLD["q17"], v2["q17"])[0] is False  # answered, should refuse
    assert eh.check_faithful(GOLD["q16"], v2["q16"])[0] is True   # a refusal claims nothing
    print("OK — layer 2: invented number caught, refusal faithful, off-topic answer not")


def test_grounded_without_a_golden_set():
    v2 = eh.load_responses("v2")
    assert eh.key_facts("The Q3 offsite is in Lisbon on October 14th.") == ["Q3", "Lisbon", "October", "14"]
    assert eh.check_grounded(v2["q01"])[0] is True
    assert eh.check_grounded(v2["q06"])[0] is False                # 50 EUR, passage says 40
    assert eh.check_grounded(v2["q02"])[0] is False                # invents a twelve-hour rule
    print("OK — production layer 2: numbers and names must be in the passage (no golden set needed)")


def test_layer3_runs_only_after_cheap_layers():
    calls = []

    def fake_judge(item, resp):
        calls.append(item["id"])
        return {"verdict": "pass", "reason": "fake"}

    cases = eh.run_version(GOLDEN, eh.load_responses("v2"), None, judge=fake_judge)
    skipped = {c["id"] for c in cases if not (c["l1"][0] and c["l2"][0])}
    assert skipped == {"q06", "q16", "q17"}, skipped
    assert not skipped & set(calls), calls
    assert len(calls) == 18 - len(skipped), calls
    print(f"OK — layer 3: judge called {len(calls)} times, never on the {len(skipped)} cases L1/L2 failed")


# --- 3. the proof point -----------------------------------------------------
def test_proof_numbers():
    m1, m2 = eh.metrics(_scored("v1")), eh.metrics(_scored("v2"))
    assert (m1["faithfulness"]["passed"], m1["faithfulness"]["total"]) == (17, 18), m1
    assert (m2["faithfulness"]["passed"], m2["faithfulness"]["total"]) == (16, 18), m2
    assert f"{m1['faithfulness']['rate']:.0%}" == "94%" and f"{m2['faithfulness']['rate']:.0%}" == "89%"
    assert m2["correctness"]["rate"] > m1["correctness"]["rate"], "v2 correctness must go UP"
    print("OK — faithfulness 17/18 = 94% → 16/18 = 89%, while correctness goes up")


def test_gates():
    m1, m2 = eh.metrics(_scored("v1")), eh.metrics(_scored("v2"))
    assert eh.gate(m1) == [], "v1 alone must ship"
    problems = eh.gate(m2, m1)
    assert [p["metric"] for p in problems] == ["faithfulness"], problems
    cases = {c["id"]: c for c in _scored("v2")}
    line = eh.headline(problems[0], cases)
    assert line == "faithfulness 94% → 89% (case q17: answered a question it should refuse)", line
    assert eh.average_gate(m2, m1) is True, "the average-only gate must ship v2"
    print("OK — per-metric gate BLOCKS v2 on q17; average-only gate would SHIP it")


def test_exit_codes():
    assert _quiet(eh.main, []) == 1
    assert _quiet(eh.main, ["--brief"]) == 1
    assert _quiet(eh.main, ["--version", "v1"]) == 0
    assert _quiet(eh.main, ["--calibrate"]) == 0
    print("OK — exit codes: default 1 (BLOCKED), --version v1 0 (SHIP), --calibrate 0")


def test_live_without_sentence_transformers_exits_2():
    saved = sys.modules.get("sentence_transformers", "absent")
    sys.modules["sentence_transformers"] = None          # make the import fail, installed or not
    err = io.StringIO()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            eh.main(["--live"])
        raise AssertionError("--live without sentence-transformers should exit")
    except SystemExit as e:
        assert e.code == 2, e.code
    finally:
        if saved == "absent":
            del sys.modules["sentence_transformers"]
        else:
            sys.modules["sentence_transformers"] = saved
    assert "needs sentence-transformers" in err.getvalue(), err.getvalue()
    print("OK — --live without sentence-transformers: message on stderr, exit code 2")


def test_calibration():
    judge, humans = eh.load_judge("v2"), eh.load_humans()
    assert len(humans) == 18
    diffs = {i: (judge[i]["verdict"], h["label"]) for i, h in humans.items()
             if judge[i]["verdict"] != h["label"]}
    assert diffs.get("q02") == ("pass", "fail"), diffs   # fluent but wrong
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        eh.main(["--calibrate"])
    text = out.getvalue()
    assert "16/18" in text and "fluent but wrong" in text and "guess with a decimal point" in text
    print("OK — calibration: 16/18 agree; q02 is fluent but wrong (judge PASS, human FAIL)")


# --- 4. the exercises -------------------------------------------------------
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
    for n in (1, 2, 3, 4):
        name = f"your_turn_{n}"
        mod = _load(name)
        assert _quiet(mod.grade) == 1, f"{name}: the stub should be BLOCKED"
        exec(_spoiler(name), mod.__dict__)
        assert _quiet(mod.grade) == 0, f"{name}: the spoiler should SHIP"
    print("OK — your_turn_1..4: stub → BLOCKED, spoiler solution → SHIP")


if __name__ == "__main__":
    eh.banner()
    print("  " + eh._c("2", "tests · golden set, layers, gate, calibration, exercises (no models)\n"))
    test_golden_shape()
    test_golden_only_real_handbook_files_and_facts()
    test_layer1_programmatic()
    test_layer2_grounded()
    test_grounded_without_a_golden_set()
    test_layer3_runs_only_after_cheap_layers()
    test_proof_numbers()
    test_gates()
    test_exit_codes()
    test_live_without_sentence_transformers_exits_2()
    test_calibration()
    test_your_turns()
    print("\n" + eh._c("32", "ALL TESTS PASSED"))
