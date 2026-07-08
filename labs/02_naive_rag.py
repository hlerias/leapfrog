# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
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
