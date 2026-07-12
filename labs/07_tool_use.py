# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Lab 07 — Give the model a tool                             Ch 6
# Needs a model with tool calling.
#
# WHAT IT IS    An agent stripped to its core: the model proposes a function
#               call, YOUR code runs it, and the result goes back.
# HOW IT WORKS  1) declare one tool   2) loop: model -> tool_calls ->
#               you run them -> feed results back -> repeat until it answers
# PROOF POINT   The model calls get_headcount, your code runs the real
#               function, and it composes the answer from what you returned.
# WHY DO IT     "Model proposes, your code disposes" is the whole basis of
#               agents — and exactly where least privilege lives.
#
# Run:  export LLM_API_KEY=...   then   python labs/07_tool_use.py
# pip install requests
import os, json, requests

print("── Leapfrog Labs · Lab 07 — Give the model a tool ──")
print("Watch: the model calls your get_headcount function, then composes the answer.\n")

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
API_KEY  = os.environ.get("LLM_API_KEY")
MODEL    = os.environ.get("LLM_MODEL", "gpt-4o-mini")

if not API_KEY:
    raise SystemExit("This lab needs a model with tool calling. export LLM_API_KEY=... "
                     "(or a local Ollama that supports tools). See the README.")

def get_headcount(team):                       # the one real thing it may do
    return {"platform": 42, "design": 9, "data": 17}.get(team.lower(), 0)

tools = [{"type": "function", "function": {"name": "get_headcount",
  "description": "Number of people on a team",
  "parameters": {"type": "object", "properties": {"team": {"type": "string"}}, "required": ["team"]}}}]

msgs = [{"role": "user", "content": "Is the platform team bigger than design?"}]

def chat(m):
    try:
        r = requests.post(f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"model": MODEL, "messages": m, "tools": tools}, timeout=60).json()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Could not reach the model at {BASE_URL}: {e}")
    return r["choices"][0]["message"]

m = chat(msgs)
while m.get("tool_calls"):                      # the agent loop
    msgs.append(m)
    for tc in m["tool_calls"]:
        args = json.loads(tc["function"]["arguments"])
        result = get_headcount(**args)
        print(f"  model asked get_headcount({args})  ->  your code returned {result}")
        msgs.append({"role": "tool", "tool_call_id": tc["id"],
                     "content": json.dumps(result)})
    m = chat(msgs)

print("\nFinal answer:", m["content"])
