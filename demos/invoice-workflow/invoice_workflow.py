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
# human. Two ways to run the model, both local and free:
#   LLM_BACKEND=ollama       (default) any OpenAI-compatible endpoint
#   LLM_BACKEND=transformers            in-process on your GPU/CPU via Hugging
#                                       Face — no server, no sudo, ideal for
#                                       locked-down machines where Ollama's
#                                       hosts are blocked but Hugging Face works

import argparse
import glob
import json
import os
import sys

import requests

# --- config (same env vars as every other Leapfrog lab) ---------------------
BACKEND = os.environ.get("LLM_BACKEND", "ollama")     # "ollama" | "transformers"
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("LLM_API_KEY", "ollama")
MODEL = os.environ.get("LLM_MODEL", "llama3.2")
HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")  # transformers backend

APPROVAL_THRESHOLD = float(os.environ.get("APPROVAL_THRESHOLD", "1000"))  # EUR
TOLERANCE = 0.01  # rounding slack when checking that the numbers add up
ROUTES = {"auto-approve", "needs-approval", "hold-review"}  # the only valid outcomes

SCHEMA = (
    'Return ONLY a JSON object with exactly these keys: '
    '{"vendor": string|null, "invoice_number": string|null, '
    '"invoice_date": string|null, "currency": string|null, '
    '"line_items": [{"description": string, "amount": number}], '
    '"subtotal": number|null, "tax": number|null, "total": number|null}. '
    'The "vendor" is the company that ISSUED the invoice (the sender at the top), '
    'NOT the "bill to" / customer it was sent to. '
    "Amounts must be plain numbers with no currency symbols or thousands "
    "separators. If a field is missing or unreadable, use null — never guess a number."
)


# --- 1. EXTRACT -------------------------------------------------------------
def extract(raw_text):
    """Dispatch to the configured backend. Both are local and free."""
    generate = _hf_generate if BACKEND == "transformers" else _chat
    return _extract_with(generate, raw_text)


def _extract_with(generate, raw_text, retries=1):
    """Shared loop: ask the model for JSON, validate, and retry once with the
    error fed back — the same for every backend. Only `generate` differs."""
    msgs = [
        {"role": "system", "content": "You extract data from invoices. " + SCHEMA},
        {"role": "user", "content": f"INVOICE:\n{raw_text}\n\nExtract it as JSON."},
    ]
    last_err = "no response"
    for _ in range(retries + 1):
        raw = generate(msgs)
        obj, err = _parse_and_check(raw)
        if obj is not None:
            return obj
        last_err = err
        msgs.append({"role": "user", "content": f"That was invalid ({err}). " + SCHEMA})
    raise ValueError(f"model never returned valid JSON: {last_err}")


# backwards-compatible alias (tests and older callers use this name)
def extract_via_llm(raw_text):
    return _extract_with(_chat, raw_text)


# --- backend A: any OpenAI-compatible endpoint (Ollama, vLLM, hosted) -------
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


# --- backend B: Hugging Face transformers, in-process on your GPU/CPU -------
# No server, no sudo. Weights download from Hugging Face on first use and cache
# in ~/.cache/huggingface. Ideal where Ollama's hosts are blocked but HF works.
_HF = {}  # lazy singleton: model + tokenizer, loaded once


def _hf_load():
    if _HF:
        return _HF
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        raise ValueError(
            "transformers backend needs torch + transformers. Install with:\n"
            "  pip install -r requirements-transformers.txt")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32   # fp16 halves VRAM
    try:
        tok = AutoTokenizer.from_pretrained(HF_MODEL)
        try:                                            # newer transformers: dtype=
            model = AutoModelForCausalLM.from_pretrained(HF_MODEL, dtype=dtype)
        except TypeError:                               # older transformers: torch_dtype=
            model = AutoModelForCausalLM.from_pretrained(HF_MODEL, torch_dtype=dtype)
    except Exception as e:
        raise ValueError(
            f"could not load '{HF_MODEL}' from Hugging Face ({type(e).__name__}). "
            "Check that huggingface.co is reachable; behind a corporate proxy you "
            "may need HTTPS_PROXY set, an HF_TOKEN, or a mirror via HF_ENDPOINT. "
            "A smaller model may also help: HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct.")
    model = model.to(device)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    _HF.update(tok=tok, model=model, device=device)
    return _HF


def _hf_generate(msgs):
    hf = _hf_load()
    tok, model = hf["tok"], hf["model"]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt").to(hf["device"])
    import torch
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=512, do_sample=False,
                             pad_token_id=tok.pad_token_id)
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


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
    """Do the numbers add up? Returns (ok, checks), where each check is
    {"text": ..., "ok": bool}. The checks drive the decision AND explain it —
    including the ones that pass, so you can see the arithmetic being verified."""
    checks = []
    total = _num(obj.get("total"))
    subtotal = _num(obj.get("subtotal"))
    tax = _num(obj.get("tax")) or 0.0
    items = [_num(li.get("amount")) for li in obj.get("line_items") or []
             if isinstance(li, dict)]
    items = [x for x in items if x is not None]

    checks.append({"ok": bool(obj.get("invoice_number")),
                   "text": "invoice number present"
                           if obj.get("invoice_number") else "no invoice number"})
    checks.append({"ok": total is not None,
                   "text": "total present" if total is not None
                           else "no total on the invoice"})

    if subtotal is not None and items:
        s = sum(items)
        good = abs(s - subtotal) <= TOLERANCE
        checks.append({"ok": good,
                       "text": (f"line items sum to {s:.2f} = subtotal {subtotal:.2f}" if good
                                else f"line items sum to {s:.2f}, but subtotal says {subtotal:.2f}")})
    if total is not None and subtotal is not None:
        st = subtotal + tax
        good = abs(st - total) <= TOLERANCE
        checks.append({"ok": good,
                       "text": (f"subtotal {subtotal:.2f} + tax {tax:.2f} = {st:.2f} = total {total:.2f}"
                                if good else
                                f"subtotal {subtotal:.2f} + tax {tax:.2f} = {st:.2f}, but total says {total:.2f}")})

    return all(c["ok"] for c in checks), checks


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
    ok, checks = reconcile(obj)
    total = _num(obj.get("total"))

    if not ok:
        route = "hold-review"
        why = "reconciliation failed — a human must look"
    elif total is not None and total > APPROVAL_THRESHOLD:
        route = "needs-approval"
        why = f"reconciled, but total {total:.2f} is over the {APPROVAL_THRESHOLD:.0f} approval limit"
    else:
        route = "auto-approve"
        why = f"reconciled, and total {total:.2f} is under the {APPROVAL_THRESHOLD:.0f} limit"

    # containment: nothing outside the allowlist can ever escape this function
    if route not in ROUTES:
        route, why = "hold-review", "route outside policy — contained"

    return {
        "vendor": obj.get("vendor"),
        "invoice_number": obj.get("invoice_number"),
        "invoice_date": obj.get("invoice_date"),
        "currency": obj.get("currency"),
        "subtotal": _num(obj.get("subtotal")),
        "tax": _num(obj.get("tax")),
        "total": total,
        "n_items": sum(1 for li in obj.get("line_items") or [] if isinstance(li, dict)),
        "checks": checks,
        "reconciled": ok,
        "route": route,
        "why": why,
        "reasons": [c["text"] for c in checks if not c["ok"]],
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
        obj = extract(open(path, encoding="utf-8").read())
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


def _fmt(v):
    return f"{v:.2f}" if isinstance(v, (int, float)) else "—"


STEP = "1;38;5;44"  # step-label colour (cyan, matches the brand)


def _print_detailed(d):
    """Narrate all four steps for one invoice, so you can see what happened."""
    print("\n" + _c("2", "─" * 60))
    print("  " + _c("1", "📄 " + d["invoice_file"]))

    if d.get("error"):
        print("  " + _c(STEP, "① EXTRACT  ") + _c("31", "✗ could not read the invoice — ")
              + d["error"])
    else:
        print("  " + _c(STEP, "① EXTRACT  ")
              + _c("2", "the model turned raw text into structured data:"))
        print("             vendor: {}   invoice: {}   date: {}".format(
            d.get("vendor") or "—", d.get("invoice_number") or "—", d.get("invoice_date") or "—"))
        print("             {} line item(s) · subtotal {} · tax {} · total {} {}".format(
            d.get("n_items", 0), _fmt(d.get("subtotal")), _fmt(d.get("tax")),
            _fmt(d.get("total")), d.get("currency") or ""))
        print("  " + _c(STEP, "② VALIDATE ") + _c("32", "✓ ")
              + _c("2", "the reply parsed as JSON and matched the schema"))

    if d.get("checks"):
        print("  " + _c(STEP, "③ RECONCILE")
              + _c("2", " the arithmetic — checked by code, not the model:"))
        for c in d["checks"]:
            mark = _c("32", "✓") if c["ok"] else _c("31", "✗")
            print(f"             {mark} {c['text']}")

    icon = ICON.get(d["route"], "?")
    col = {"auto-approve": "32", "needs-approval": "33", "hold-review": "31"}.get(d["route"], "0")
    print("  " + _c(STEP, "④ DECIDE   ") + _c(col, f"{icon} {d['route'].upper()}")
          + _c("2", " — " + d.get("why", "")))


def _print_brief(d):
    print(f"\n{ICON.get(d['route'], '?')} {d['invoice_file']}  ->  {d['route'].upper()}")
    print(f"   vendor={d.get('vendor')!r}  inv={d.get('invoice_number')!r}  "
          f"total={d.get('total')} {d.get('currency') or ''}  reconciled={d.get('reconciled')}")
    for c in d.get("checks", []):
        if not c["ok"]:
            print(f"   · {c['text']}")
    if d.get("error"):
        print(f"   · {d['error']}")


def main():
    ap = argparse.ArgumentParser(description="Leapfrog invoice-triage demo")
    ap.add_argument("--offline", action="store_true",
                    help="use canned fixture extractions (no model, no network)")
    ap.add_argument("--brief", action="store_true",
                    help="terse one-block-per-invoice output instead of the explained view")
    ap.add_argument("--file", help="process a single invoice file")
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "sample_invoices"))
    args = ap.parse_args()

    files = [args.file] if args.file else sorted(glob.glob(os.path.join(args.dir, "*.txt")))
    if not files:
        print("no invoices found", file=sys.stderr)
        return 2

    banner()
    if args.offline:
        mode = "OFFLINE (canned extractions, no model)"
    elif BACKEND == "transformers":
        mode = f"TRANSFORMERS (local, GPU/CPU) — {HF_MODEL}"
    else:
        mode = f"OLLAMA {MODEL} @ {BASE_URL}"
    print(f"  extractor: {mode}")
    print(_c("2", "─" * 60))

    if not args.brief:
        print(_c("2",
            "\n  Accounts-Payable triage. For each invoice below, a LOCAL model reads the\n"
            "  messy text into structured data — that is the only thing it does. Then plain\n"
            "  code VALIDATES the JSON, RECONCILES the arithmetic, and a bounded policy\n"
            "  DECIDES the route. The model can misread or invent a number; watch step ③\n"
            "  catch it. The route is always chosen by code, never by the model.\n"))

    results = []
    for f in files:
        try:
            d = process(f, args.offline)
        except Exception as e:
            d = {"invoice_file": os.path.basename(f), "route": "hold-review",
                 "reconciled": False, "checks": [], "reasons": [], "error": str(e),
                 "why": "extraction failed — sent to a human", "vendor": None,
                 "invoice_number": None, "invoice_date": None, "currency": None,
                 "subtotal": None, "tax": None, "total": None, "n_items": 0}
        results.append(d)
        (_print_brief if args.brief else _print_detailed)(d)

    # acceptance summary: every invoice must have produced a valid, bounded route
    print("\n" + _c("2", "─" * 60))
    by = {r: sum(1 for d in results if d["route"] == r) for r in sorted(ROUTES)}
    print("  routes:  " + "    ".join(f"{k}={v}" for k, v in by.items()))
    bad = [d["invoice_file"] for d in results if d["route"] not in ROUTES]
    if bad:
        print("  " + _c("31", "FAIL — invoices escaped the allowlist: ") + str(bad))
        return 1
    print("  " + _c("32", f"OK — {len(results)} invoice(s) processed, every route within policy."))
    if not args.brief:
        held = by.get("hold-review", 0)
        print(_c("2",
            "\n  Takeaway: the model never chose a route or did the maths — it only turned\n"
            "  messy text into structure. When it (or the invoice) was wrong, reconciliation\n"
            f"  caught it and a human gets it ({held} held here). That gap between what a\n"
            "  model *reads* and what code *decides* is what makes this safe to ship.\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
