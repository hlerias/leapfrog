# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# Tests the grounded-Q&A decision logic with a fake retriever — no models,
# no network. (The retrieval itself is the same bi-encoder + cross-encoder as
# lab 06, proven there.)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ask  # noqa: E402


def hit(_q):   # a confidently relevant result, best first
    return [("Book travel at least three weeks ahead.", "travel.txt", 6.2),
            ("Alcohol is not reimbursable.", "expenses.txt", -3.0)]


def miss(_q):  # nothing relevant — top score is negative
    return [("Alcohol is not reimbursable.", "expenses.txt", -9.5)]


def test_grounded_answer():
    r = ask.answer_question("how far ahead do I book travel?", hit, threshold=0.0)
    assert r["refused"] is False, r
    assert r["source"] == "travel.txt" and "three weeks" in r["answer"], r
    assert r["score"] == 6.2, r
    print("OK — relevant question -> grounded answer, cited to travel.txt")


def test_refusal():
    r = ask.answer_question("what's the remote-work policy?", miss, threshold=0.0)
    assert r["refused"] is True, r          # BOUNDED: never guesses
    print("OK — off-topic question -> honest refusal, no guess")


def test_model_phrasing():
    r = ask.answer_question("how far ahead?", hit, threshold=0.0,
                            phrase=lambda q, p: "About three weeks.")
    assert r["answer"] == "About three weeks.", r
    assert r["passage"].startswith("Book travel"), r    # still cites the source passage
    print("OK — with a model, answer is phrased FROM the passage (still grounded)")


def test_load_chunks_tracks_sources():
    chunks = ask.load_chunks()
    assert len(chunks) > 0, "no handbook loaded"
    srcs = {c[1] for c in chunks}
    assert {"travel.txt", "expenses.txt", "oncall.txt", "offsites.txt"} <= srcs, srcs
    print(f"OK — loaded {len(chunks)} passages from {len(srcs)} handbook files")


if __name__ == "__main__":
    ask.banner()
    print("  " + ask._c("2", "tests · grounded-Q&A decision logic (no models)\n"))
    test_grounded_answer()
    test_refusal()
    test_model_phrasing()
    test_load_chunks_tracks_sources()
    print("\n" + ask._c("32", "ALL TESTS PASSED"))
