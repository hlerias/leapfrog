# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
# pip install requests
import requests, os, json

BASE_URL=os.environ.get("LLM_BASE_URL","https://api.openai.com/v1")
API_KEY=os.environ["LLM_API_KEY"]; MODEL=os.environ.get("LLM_MODEL","gpt-4o-mini")

def get_headcount(team):                       # the one real thing it may do
    return {"platform":42,"design":9,"data":17}.get(team.lower(),0)

tools=[{"type":"function","function":{"name":"get_headcount",
  "description":"Number of people on a team",
  "parameters":{"type":"object","properties":{"team":{"type":"string"}},"required":["team"]}}}]

msgs=[{"role":"user","content":"Is the platform team bigger than design?"}]
def chat(m):
    return requests.post(f"{BASE_URL}/chat/completions",
        headers={"Authorization":f"Bearer {API_KEY}"},
        json={"model":MODEL,"messages":m,"tools":tools}).json()["choices"][0]["message"]

m=chat(msgs)
while m.get("tool_calls"):                      # the agent loop
    msgs.append(m)
    for tc in m["tool_calls"]:
        args=json.loads(tc["function"]["arguments"])
        msgs.append({"role":"tool","tool_call_id":tc["id"],
                     "content":json.dumps(get_headcount(**args))})
    m=chat(msgs)
print(m["content"])
