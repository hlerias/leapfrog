# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 02 — Watch naive RAG fail                              Ch 7
# No API key — first run downloads a small local model.
#
# WHAT IT IS    Your first RAG, and why it breaks on the second question.
# HOW IT WORKS  1) embed four short facts   2) embed the question
#               3) return the single closest fact by cosine similarity
# PROOF POINT   Ask for the "next" offsite and top-1 hands back Berlin (Q2),
#               not Lisbon (Q3). Seeing the wrong answer *is* the lesson.
# WHY DO IT     You can't fix retrieval you haven't watched fail — this is
#               the exact failure every production RAG starts from.
#
# Run:  python labs/02_naive_rag.py
# pip install sentence-transformers numpy
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")   # small, local, free
docs = [
  "The Q3 offsite is in Lisbon on October 14th.",
  "The Q2 offsite was in Berlin on April 9th.",
  "Reimbursements over 500 EUR need VP approval.",
  "Book travel via the tool at least 3 weeks ahead.",
]
emb = model.encode(docs, normalize_embeddings=True)

def retrieve(q, k=1):
    qv = model.encode([q], normalize_embeddings=True)[0]
    scores = emb @ qv
    return [(docs[i], round(float(scores[i]), 3)) for i in scores.argsort()[::-1][:k]]

for q in ["Where is the NEXT offsite?", "What's the limit before I need sign-off?"]:
    print(q, "->", retrieve(q))
