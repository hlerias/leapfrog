# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
# pip install requests
import requests, os

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
API_KEY  = os.environ["LLM_API_KEY"]            # export LLM_API_KEY=sk-...
MODEL    = os.environ.get("LLM_MODEL", "gpt-4o-mini")
PRICE_IN, PRICE_OUT = 0.15, 0.60                # $ per 1M tokens — set YOUR model's

r = requests.post(f"{BASE_URL}/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"model": MODEL, "messages": [
        {"role": "user", "content": "In two sentences, what is retrieval-augmented generation?"}]},
).json()

print(r["choices"][0]["message"]["content"])
u = r["usage"]
cost = u["prompt_tokens"]/1e6*PRICE_IN + u["completion_tokens"]/1e6*PRICE_OUT
print(f"\nin={u['prompt_tokens']}  out={u['completion_tokens']}  cost=${cost:.6f}")
