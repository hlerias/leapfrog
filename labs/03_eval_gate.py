# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
GOLDEN = [
  {"q": "Capital of Portugal?",        "must_include": ["Lisbon"]},
  {"q": "2 + 2 * 3 = ?",               "must_include": ["8"]},
  {"q": "Who wrote the book Leapfrog?", "must_include": ["Hugo", "Lerias"]},
]

def score(ans, item):
    return all(k.lower() in ans.lower() for k in item["must_include"])

def run_eval(answer_fn, threshold=0.90):
    rows = [(it["q"], score(answer_fn(it["q"]), it)) for it in GOLDEN]
    rate = sum(ok for _, ok in rows) / len(rows)
    for q, ok in rows: print("PASS" if ok else "FAIL", "-", q)
    print(f"\nscore {rate:.0%}  ->  {'SHIP' if rate >= threshold else 'BLOCKED'}")
    return rate >= threshold

# plug in your real model from Lab 1 in place of this stub:
run_eval(lambda q: "Lisbon; 8; by Hugo Lerias")
