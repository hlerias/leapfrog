# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Ask the handbook — grounded Q&A, not a chatbot
#
# The book warns against open-ended chatbots that bluff. This is the opposite,
# and it's the natural extension of the RAG labs (02 + 06). A human asks a
# question; the tool answers ONLY from a fixed set of documents, SHOWS its
# source, and REFUSES honestly when it can't find the answer. Three guardrails,
# straight from the chapters:
#
#   GROUNDED   every answer comes from a retrieved passage, and it's cited
#   BOUNDED    below a confidence threshold it says "not in the handbook" —
#              it never guesses (containment, lab 09)
#   ONE JOB    it answers questions about THIS handbook, not "anything"
#
# By default it answers offline by showing the cited passage. If a local model
# is configured (--model, or LLM_API_KEY set), the model phrases the answer
# using ONLY that passage — grounded generation, still cited, still able to
# refuse. No API key needed for the default path; first run downloads two small
# retrieval models (~180 MB), same as lab 06.

import argparse
import glob
import os
import re
import sys

HANDBOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handbook")
THRESHOLD = float(os.environ.get("ASK_THRESHOLD", "0.0"))  # cross-encoder cutoff


# --- load + chunk the handbook (source tracked for citations) ---------------
def load_chunks(folder=HANDBOOK):
    chunks = []                      # list of (text, source_filename)
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        src = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
            sent = sent.strip()
            if sent:
                chunks.append((sent, src))
    return chunks


# --- retrieval: bi-encoder recall, then cross-encoder rerank (lab 06) --------
_STATE = {}


def _retriever(chunks):
    """Lazily load the two small models and embed the handbook once."""
    if "retrieve" in _STATE:
        return _STATE["retrieve"]
    try:
        from sentence_transformers import SentenceTransformer, CrossEncoder
    except ImportError:
        raise SystemExit("This demo needs sentence-transformers:\n"
                         "  pip install -r requirements.txt   (or ./setup.sh)")
    bi = SentenceTransformer("all-MiniLM-L6-v2")               # fast recall
    ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")  # precise rerank
    emb = bi.encode([c[0] for c in chunks], normalize_embeddings=True)

    def retrieve(question, k=5):
        qv = bi.encode([question], normalize_embeddings=True)[0]
        top = (emb @ qv).argsort()[::-1][:k]                   # 1) cheap recall
        cand = [chunks[i] for i in top]
        scored = ce.predict([(question, c[0]) for c in cand])  # 2) precise rerank
        ranked = sorted(zip(cand, scored), key=lambda x: -x[1])
        return [(c[0], c[1], float(s)) for c, s in ranked]     # (text, source, score)

    _STATE["retrieve"] = retrieve
    return retrieve


# --- the decision (pure logic — no model, unit-testable) --------------------
def answer_question(question, retrieve, threshold=THRESHOLD, phrase=None):
    """Return a grounded answer, or an honest refusal.

    retrieve(question) -> list of (passage, source, score), best first.
    phrase(question, passage) -> a model-phrased answer, or None to show the passage.
    """
    results = retrieve(question)
    if not results or results[0][2] < threshold:            # BOUNDED: refuse, never guess
        return {"refused": True,
                "message": "I couldn't find that in the handbook.",
                "score": round(results[0][2], 2) if results else None}
    passage, source, score = results[0]
    answer = phrase(question, passage) if phrase else passage
    return {"refused": False, "answer": answer, "source": source,   # GROUNDED + cited
            "passage": passage, "score": round(score, 2)}


# --- optional: let a local model phrase the answer FROM the passage ---------
def phrase_with_model(question, passage):
    import requests
    base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", "llama3.2")
    system = ("Answer the question using ONLY the text provided. Be brief. "
              "Do not add anything not in the text. If the text does not answer "
              "the question, reply exactly: The handbook doesn't cover that.")
    try:
        r = requests.post(f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "temperature": 0, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Text:\n{passage}\n\nQuestion: {question}"}]},
            timeout=60).json()
        return r["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(couldn't reach the model — showing the passage instead)\n{passage}  [{e}]"


# --- presentation -----------------------------------------------------------
def _c(code, s):
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def banner():
    rule = _c("2", "─" * 60)
    print(rule)
    print("  " + _c("1;38;5;44", "Leapfrog Labs") + _c("2", " · ") + _c("1", "Ask the handbook"))
    print("  " + _c("2", "Grounded Q&A — cited, bounded, one job. Not a chatbot."))
    print("  " + _c("38;5;99", "https://leapfrog.lerias.org"))
    print(rule)


def show(question, result):
    print("\n" + _c("1", "Q: ") + question)
    if result["refused"]:
        print("  " + _c("33", "⚠ " + result["message"]))
        print("  " + _c("2", f"(best match scored {result['score']}, below the confidence "
                             f"threshold — so it won't guess)"))
        return
    print("  " + _c("32", "A: ") + result["answer"])
    print("  " + _c("2", f"source: {result['source']}   (relevance {result['score']})"))
    if result["answer"] != result["passage"]:
        print("  " + _c("2", f"grounded on: \"{result['passage']}\""))


DEMO_QUESTIONS = [
    "How far ahead should I book travel?",
    "Where is the next offsite?",
    "What's the meal limit when I'm travelling?",
    "Can I expense a bottle of wine?",
    "What is the company's policy on remote work?",   # not in the handbook -> refuse
]


def main():
    ap = argparse.ArgumentParser(description="Ask the handbook — grounded Q&A")
    ap.add_argument("--ask", help="ask one question and exit")
    ap.add_argument("--demo", action="store_true", help="run a few sample questions (incl. one it should refuse)")
    ap.add_argument("--model", action="store_true", help="let a local model phrase the answer from the passage")
    args = ap.parse_args()

    banner()
    chunks = load_chunks()
    if not chunks:
        print("no handbook documents found", file=sys.stderr)
        return 2
    sources = sorted({c[1] for c in chunks})
    print(f"  handbook: {len(chunks)} passages from {', '.join(sources)}")
    phrase = phrase_with_model if (args.model or os.environ.get("LLM_API_KEY")) else None
    print("  answers:  " + ("phrased by a local model, grounded on the passage"
                            if phrase else "the cited passage itself (add --model to phrase them)"))

    print(_c("2", "  loading the retrieval models (first run downloads ~180 MB)…"))
    retrieve = _retriever(chunks)

    if args.ask:
        show(args.ask, answer_question(args.ask, retrieve, phrase=phrase))
        return 0
    if args.demo:
        for q in DEMO_QUESTIONS:
            show(q, answer_question(q, retrieve, phrase=phrase))
        return 0

    print(_c("2", "\n  Ask a question about the handbook (or 'quit'):"))
    while True:
        try:
            q = input(_c("1", "\n> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"quit", "exit", "q", ""}:
            break
        show(q, answer_question(q, retrieve, phrase=phrase))
    return 0


if __name__ == "__main__":
    sys.exit(main())
