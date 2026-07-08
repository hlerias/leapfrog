# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
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
