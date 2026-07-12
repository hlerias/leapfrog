# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 08 — Trace one request                                 Ch 9
# No API key — runs as-is with a fake call.
#
# WHAT IT IS    One request captured as a single span: inputs, output,
#               tokens, latency — the seed of real observability.
# HOW IT WORKS  1) wrap a call   2) time it, capture tokens and errors
#               3) emit a JSON span you'd ship to your tracer
# PROOF POINT   You get the whole request path as one record, with a real
#               latency_ms — not just the model's name.
# WHY DO IT     You can't debug what you can't see. When quality drops (and
#               per Ch 8 the model usually isn't the culprit), this is what you read.
#
# Run:  python labs/08_trace.py
import time, json, uuid

print("── Leapfrog Labs · Lab 08 — Trace one request ──")
print("Watch: the whole request path — inputs, tokens, latency — as one JSON span.\n")

def traced(call_fn, **inputs):
    span = {"id": str(uuid.uuid4())[:8], "inputs": inputs, "_t": time.time()}
    try:
        out = call_fn(**inputs)
        span["tokens"] = out.get("tokens"); span["ok"] = True
    except Exception as e:
        span["ok"] = False; span["error"] = str(e); raise
    finally:
        span["latency_ms"] = round((time.time() - span.pop("_t")) * 1000)
        print(json.dumps(span, indent=2))          # ship this to your tracer
    return out

# fake call so it runs with no key; swap in your Lab 1 call
def fake(prompt, model): time.sleep(0.15); return {"tokens": {"in": 812, "out": 143}}

traced(fake, prompt="Summarize Q3", model="gpt-4o-mini")
