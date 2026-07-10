# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 06 — Fix the RAG: chunk, retrieve, rerank              Ch 7
# No API key — first run downloads two small local models.
#
# WHAT IT IS    The fix for Lab 02: retrieve cheaply, then rerank precisely.
# HOW IT WORKS  1) a bi-encoder recalls the top-k candidates fast
#               2) a cross-encoder scores each (question, candidate) pair
#               3) return the highest-scoring passage
# PROOF POINT   "offsite in the autumn?" now returns Lisbon (Q3) — the passage
#               naive top-1 missed in Lab 02. Two stages beat one.
# WHY DO IT     Retrieve-then-rerank is the single biggest RAG quality upgrade,
#               and it's about fifteen lines.
#
# Run:  python labs/06_rag_rerank.py
# pip install sentence-transformers
from sentence_transformers import SentenceTransformer, CrossEncoder

bi = SentenceTransformer("all-MiniLM-L6-v2")               # fast retriever
ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")  # precise reranker

text = ("The Q2 offsite was in Berlin on April 9th. "
        "The Q3 offsite is in Lisbon on October 14th. "
        "Reimbursements over 500 EUR need VP approval. "
        "Book travel at least three weeks ahead.")
docs = [s.strip()+"." for s in text.split(". ") if s.strip()]   # sentence chunks
emb  = bi.encode(docs, normalize_embeddings=True)

def answer(q, k=4):
    qv  = bi.encode([q], normalize_embeddings=True)[0]
    top = (emb @ qv).argsort()[::-1][:k]                    # 1) cheap recall
    cand = [docs[i] for i in top]
    ranked = sorted(zip(cand, ce.predict([(q,c) for c in cand])), key=lambda x:-x[1])
    return ranked[0][0]                                     # 2) precise rerank

print(answer("Where is the offsite in the autumn?"))
