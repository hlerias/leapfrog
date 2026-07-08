# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
import time, json, uuid

def traced(call_fn, **inputs):
    span={"id":str(uuid.uuid4())[:8],"inputs":inputs,"_t":time.time()}
    try:
        out=call_fn(**inputs)
        span["tokens"]=out.get("tokens"); span["ok"]=True
    except Exception as e:
        span["ok"]=False; span["error"]=str(e); raise
    finally:
        span["latency_ms"]=round((time.time()-span.pop("_t"))*1000)
        print(json.dumps(span, indent=2))          # ship this to your tracer
    return out

# fake call so it runs with no key; swap in your Lab 1 call
def fake(prompt, model): time.sleep(0.15); return {"tokens":{"in":812,"out":143}}

traced(fake, prompt="Summarize Q3", model="gpt-4o-mini")
