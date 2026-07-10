# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
#
# Invoice Workflow demo — "putting it all together": one small, real
# Accounts-Payable workflow.
# A local language model does the ONE thing models are good at — reading a
# messy human document and turning it into structure. Everything that has to
# be *correct* — the arithmetic, the policy, the routing — is plain code the
# model never touches. That split is the whole lesson of the book, end to end:
#
#     1. EXTRACT   the model reads raw invoice text  -> structured JSON
#     2. VALIDATE  the JSON parses and fits the schema (retry if not)
#     3. RECONCILE the numbers actually add up        (code, not the model)
#     4. DECIDE    a bounded policy picks a route      (containment)
#
# The model can be wrong; the pipeline is built to catch it and fall back to a
# human. Run it against any OpenAI-compatible local model (Ollama by default).

import argparse
import glob
import json
import os
import sys

import requests

# --- config (same env vars as every other Leapfrog lab) ---------------------
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("LLM_API_KEY", "ollama")
MODEL = os.environ.get("LLM_MODEL", "llama3.2")

APPROVAL_THRESHOLD = float(os.environ.get("APPROVAL_THRESHOLD", "1000"))  # EUR
TOLERANCE = 0.01  # rounding slack when checking that the numbers add up
ROUTES = {"auto-approve", "needs-approval", "hold-review"}  # the only valid outcomes

SCHEMA = (
    'Return ONLY a JSON object with exactly these keys: '
    '{"vendor": string|null, "invoice_number": string|null, '
    '"invoice_date": string|null, "currency": string|null, '
    '"line_items": [{"description": string, "amount": number}], '
    '"subtotal": number|null, "tax": number|null, "total": number|null}. '
    "Amounts must be plain numbers with no currency symbols or thousands "
    "separators. If a field is missing or unreadable, use null."
)


# --- 1. EXTRACT -------------------------------------------------------------
def extract_via_llm(raw_text, retries=1):
    """Ask the local model for structured JSON; validate and retry once."""
    msgs = [
        {"role": "system", "content": "You extract data from invoices. " + SCHEMA},
        {"role": "user", "content": f"INVOICE:\n{raw_text}\n\nExtract it as JSON."},
    ]
    last_err = "no response"
    for _ in range(retries + 1):
        raw = _chat(msgs)
        obj, err = _parse_and_check(raw)
        if obj is not None:
            return obj
        last_err = err
        msgs.append({"role": "user", "content": f"That was invalid ({err}). " + SCHEMA})
    raise ValueError(f"model never returned valid JSON: {last_err}")


def _chat(msgs):
    try:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"model": MODEL, "messages": msgs,
                  "response_format": {"type": "json_object"}, "temperature": 0},
            timeout=120,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ValueError(f"no model reachable at {BASE_URL} — is Ollama running? "
                         f"(try ./run.sh, or python invoice_workflow.py --offline)")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"model request failed: {e}")
    return r.json()["choices"][0]["message"]["content"]


def _loads(raw):
    """Parse JSON the way real small models emit it: maybe fenced in ```json,
    maybe wrapped in prose. Fall back to the first {...} block in the text."""
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _parse_and_check(raw):
    """Return (obj, None) if it parses to something invoice-shaped, else (None, reason).

    Tolerant of how small local models really behave: code fences, surrounding
    prose, null/absent line_items. Rejects JSON that isn't an invoice at all.
    """
    obj = _loads(raw)
    if not isinstance(obj, dict):
        return None, "not a JSON object"
    # normalise: fill in the keys the rest of the pipeline expects
    for key in ("vendor", "invoice_number", "invoice_date", "currency",
                "subtotal", "tax", "total"):
        obj.setdefault(key, None)
    if not isinstance(obj.get("line_items"), list):  # null, missing, or wrong type
        obj["line_items"] = []
    # sanity: does this even look like an invoice? (guards against unrelated JSON)
    if _num(obj["total"]) is None and _num(obj["subtotal"]) is None and not obj["line_items"]:
        return None, "no total, subtotal, or line items — not invoice-shaped"
    return obj, None


# --- 2/3. VALIDATE + RECONCILE (no model — this must be correct) ------------
def reconcile(obj):
    """Do the numbers add up? Returns (ok: bool, reasons: list[str])."""
    reasons = []
    total = _num(obj.get("total"))
    subtotal = _num(obj.get("subtotal"))
    tax = _num(obj.get("tax")) or 0.0
    items = [_num(li.get("amount")) for li in obj.get("line_items") or []
             if isinstance(li, dict)]
    items = [x for x in items if x is not None]

    if total is None:
        reasons.append("no total on the invoice")
    if not obj.get("invoice_number"):
        reasons.append("no invoice number")

    if subtotal is not None and items:
        if abs(sum(items) - subtotal) > TOLERANCE:
            reasons.append(f"line items sum to {sum(items):.2f}, subtotal says {subtotal:.2f}")
    if total is not None and subtotal is not None:
        if abs((subtotal + tax) - total) > TOLERANCE:
            reasons.append(f"subtotal+tax = {subtotal + tax:.2f}, total says {total:.2f}")

    return (len(reasons) == 0), reasons


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace("EUR", "").strip())
    except ValueError:
        return None


# --- 4. DECIDE (bounded policy — the model never chooses the route) ---------
def decide(obj):
    ok, reasons = reconcile(obj)
    total = _num(obj.get("total"))

    if not ok:
        route = "hold-review"
    elif total is not None and total > APPROVAL_THRESHOLD:
        route = "needs-approval"
        reasons = [f"total {total:.2f} over {APPROVAL_THRESHOLD:.0f} threshold"]
    else:
        route = "auto-approve"

    # containment: nothing outside the allowlist can ever escape this function
    if route not in ROUTES:
        route = "hold-review"

    return {
        "vendor": obj.get("vendor"),
        "invoice_number": obj.get("invoice_number"),
        "currency": obj.get("currency"),
        "total": total,
        "reconciled": ok,
        "route": route,
        "reasons": reasons,
    }


# --- offline extraction: canned "correct extractions" so the pipeline can be
# seen with no model and no network. These fixtures are what a good model
# returns; loading them lets you (and the test suite) watch steps 2-4 decide.
# The real demo uses extract_via_llm() above — this is only for --offline.
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def extract_offline(path):
    fx = os.path.join(FIXTURES, os.path.splitext(os.path.basename(path))[0] + ".json")
    if not os.path.exists(fx):
        raise FileNotFoundError(f"no offline fixture for {os.path.basename(path)}")
    with open(fx, encoding="utf-8") as fh:
        return json.load(fh)


# --- driver -----------------------------------------------------------------
def process(path, offline):
    if offline:
        obj = extract_offline(path)
    else:
        obj = extract_via_llm(open(path, encoding="utf-8").read())
    d = decide(obj)
    d["invoice_file"] = os.path.basename(path)
    return d


ICON = {"auto-approve": "✓", "needs-approval": "→", "hold-review": "⚠"}


def _c(code, s):
    """ANSI colour, unless output is piped or NO_COLOR is set."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def banner():
    rule = _c("2", "─" * 60)
    print(rule)
    print("  " + _c("1;38;5;44", "Leapfrog Labs")
          + _c("2", " · ") + _c("1", "Invoice Workflow"))
    print("  " + _c("2", "The book is the why. This is where you build."))
    print("  " + _c("38;5;99", "https://leapfrog.lerias.org"))
    print(rule)


def main():
    ap = argparse.ArgumentParser(description="Leapfrog invoice-triage demo")
    ap.add_argument("--offline", action="store_true",
                    help="use canned fixture extractions (no model, no network)")
    ap.add_argument("--file", help="process a single invoice file")
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "sample_invoices"))
    args = ap.parse_args()

    files = [args.file] if args.file else sorted(glob.glob(os.path.join(args.dir, "*.txt")))
    if not files:
        print("no invoices found", file=sys.stderr)
        return 2

    banner()
    mode = ("OFFLINE (canned extractions, no model)" if args.offline
            else f"LOCAL MODEL {MODEL} @ {BASE_URL}")
    print(f"  extractor: {mode}")
    print(_c("2", "─" * 60))

    results = []
    for f in files:
        try:
            d = process(f, args.offline)
        except Exception as e:
            d = {"invoice_file": os.path.basename(f), "route": "hold-review",
                 "reconciled": False, "reasons": [f"pipeline error: {e}"],
                 "vendor": None, "invoice_number": None, "total": None, "currency": None}
        results.append(d)
        print(f"\n{ICON.get(d['route'], '?')} {d['invoice_file']}  ->  {d['route'].upper()}")
        print(f"   vendor={d['vendor']!r}  inv={d['invoice_number']!r}  "
              f"total={d['total']} {d['currency'] or ''}  reconciled={d['reconciled']}")
        if d["reasons"]:
            for reason in d["reasons"]:
                print(f"   · {reason}")

    # acceptance summary: every invoice must have produced a valid, bounded route
    print("\n" + _c("2", "─" * 60))
    by = {r: sum(1 for d in results if d["route"] == r) for r in sorted(ROUTES)}
    print("routes:", "  ".join(f"{k}={v}" for k, v in by.items()))
    bad = [d["invoice_file"] for d in results if d["route"] not in ROUTES]
    if bad:
        print("FAIL — invoices escaped the allowlist:", bad)
        return 1
    print(f"OK — {len(results)} invoice(s) processed, every route within policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
