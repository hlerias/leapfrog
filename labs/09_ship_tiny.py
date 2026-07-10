# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 09 — Ship something tiny, end to end             Interlude
# No API key — runs local, with an optional model call.
#
# WHAT IT IS    The whole book in one small shippable thing: ground a
#               decision, structure it, and refuse to act outside its bounds.
# HOW IT WORKS  1) ground the ticket on a real policy (embeddings)
#               2) make a structured decision   3) contain it to an allowlist
# PROOF POINT   It grounds on the right policy, returns a structured route,
#               and falls back safely when the model picks a disallowed one.
# WHY DO IT     Retrieval + structured output + containment in ~50 lines is
#               the five percent that makes AI actually shippable.
#
# Run:  python labs/09_ship_tiny.py
# pip install sentence-transformers   (model call optional; stub included)
from sentence_transformers import SentenceTransformer
import json

POLICIES=["Refunds over 500 EUR need manager approval.",
          "Outages are P1 and page on-call immediately.",
          "Billing questions go to finance, not engineering."]
bi=SentenceTransformer("all-MiniLM-L6-v2"); pe=bi.encode(POLICIES, normalize_embeddings=True)
def grounding(q): return POLICIES[int((pe@bi.encode([q],normalize_embeddings=True)[0]).argmax())]

ALLOWED={"finance","on-call","support"}            # the bound: nothing else is valid

def triage(ticket, decide):
    policy=grounding(ticket)                        # 1) ground it
    d=decide(ticket, policy)                        # 2) structured decision
    if d.get("route") not in ALLOWED:               # 3) contain it
        d={"route":"support","priority":3,"note":"fell back: disallowed route"}
    return {"ticket":ticket,"policy_used":policy,**d}

def decide_stub(ticket, policy):                    # swap for a real Lab 5 call
    return {"route":"on-call","priority":1} if "down" in ticket.lower() else {"route":"finance","priority":3}

print(json.dumps(triage("The billing page has been down for an hour!", decide_stub), indent=2))
