# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 05 — Make it do one real thing: structured output      Ch 6
# Needs a model with JSON mode (or any model + the retry below).
#
# WHAT IT IS    The moment output stops being chat and becomes data your
#               code can act on — JSON, validated, with a self-correcting retry.
# HOW IT WORKS  1) ask for a strict JSON shape   2) parse and validate it
#               3) if it's wrong, re-ask with the error (validate-and-retry)
# PROOF POINT   You get back {sentiment, priority, tags} you can branch on —
#               and it fixes itself when the first reply is malformed.
# WHY DO IT     Every embedded AI feature rests on reliable structured output;
#               this validate-and-retry loop is the durable pattern behind it.
#
# Run:  export LLM_API_KEY=...   then   python labs/05_structured_output.py
# pip install requests
import requests, os, json

BASE_URL=os.environ.get("LLM_BASE_URL","https://api.openai.com/v1")
API_KEY=os.environ["LLM_API_KEY"]; MODEL=os.environ.get("LLM_MODEL","gpt-4o-mini")

SPEC = ('Return ONLY JSON: '
        '{"sentiment":"positive|neutral|negative","priority":1-5,"tags":[string]}')

def call(msgs):
    r=requests.post(f"{BASE_URL}/chat/completions",
        headers={"Authorization":f"Bearer {API_KEY}"},
        json={"model":MODEL,"messages":msgs,"response_format":{"type":"json_object"}}).json()
    return r["choices"][0]["message"]["content"]

def valid(o):
    return (o.get("sentiment") in {"positive","neutral","negative"}
            and isinstance(o.get("priority"),int) and 1<=o["priority"]<=5
            and isinstance(o.get("tags"),list))

msgs=[{"role":"system","content":"Triage support tickets. "+SPEC},
      {"role":"user","content":"The dashboard is down and customers are furious."}]

for _ in range(2):
    raw=call(msgs)
    try: obj=json.loads(raw)
    except json.JSONDecodeError: obj=None
    if obj and valid(obj): print("OK ->", obj); break
    msgs.append({"role":"user","content":"That was invalid. "+SPEC})
