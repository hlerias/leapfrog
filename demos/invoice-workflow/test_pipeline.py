# Leapfrog Labs — see https://leapfrog.lerias.org — MIT licensed
#
# Invoice Workflow tests. Two kinds of check, both runnable with no model
# and no network:
#   1. GOLDEN   — the deterministic pipeline (validate -> reconcile -> decide)
#                 produces the right route for each canned extraction.
#   2. CONTRACT — the real LLM client path (extract_via_llm) is exercised
#                 against a mock OpenAI-compatible server: a good reply, a
#                 malformed-then-good reply (retry), and garbage (containment).
#
# Run:  python demos/invoice-workflow/test_pipeline.py

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import invoice_workflow as iw  # noqa: E402


# --- 1. GOLDEN: expected route per sample invoice ---------------------------
EXPECTED = {
    "acme_hardware.txt": ("auto-approve", True),
    "globex_consulting.txt": ("needs-approval", True),
    "initech_office.txt": ("hold-review", False),      # numbers don't reconcile
    "umbrella_logistics.txt": ("hold-review", False),  # missing total + invoice #
}


def test_golden():
    sample = os.path.join(HERE, "sample_invoices")
    for name, (route, reconciled) in EXPECTED.items():
        d = iw.process(os.path.join(sample, name), offline=True)
        assert d["route"] == route, f"{name}: got {d['route']}, want {route}"
        assert d["reconciled"] == reconciled, f"{name}: reconciled={d['reconciled']}"
        assert d["route"] in iw.ROUTES, f"{name}: route escaped allowlist"
    print(f"GOLDEN   ok — {len(EXPECTED)} invoices routed as expected")


# --- 2. CONTRACT: exercise the real HTTP client against a mock model ---------
GOOD = json.dumps({
    "vendor": "ACME Hardware Supply", "invoice_number": "AC-2026-0417",
    "invoice_date": "2026-03-14", "currency": "EUR",
    "line_items": [{"description": "Steel brackets", "amount": 120.0},
                   {"description": "Fasteners", "amount": 45.5},
                   {"description": "Delivery", "amount": 14.5}],
    "subtotal": 180.0, "tax": 41.4, "total": 221.4,
})

# how real small local models actually mangle output — each of these SHOULD
# parse to the right route on the FIRST call (no retry needed).
STRINGY = ('{"vendor":"ACME","invoice_number":"AC-1","currency":"EUR",'
           '"line_items":[{"description":"a","amount":"120.00"},'
           '{"description":"b","amount":"45.50"},{"description":"c","amount":"14.50"}],'
           '"subtotal":"180.00","tax":"41.40","total":"221.40"}')  # numbers as strings
NULLITEMS = ('{"vendor":"ACME","invoice_number":"AC-1","currency":"EUR",'
             '"line_items":null,"subtotal":180.0,"tax":41.4,"total":221.4}')  # null items
SEPARATORS = ('{"vendor":"Globex","invoice_number":"G-1","currency":"EUR",'
              '"line_items":[],"subtotal":"12,750.00","tax":"0.00","total":"12,750.00"}')

ROBUSTNESS = [
    ("clean json", GOOD, "auto-approve"),
    ("```json fenced```", "```json\n" + GOOD + "\n```", "auto-approve"),
    ("wrapped in prose", "Sure! Here it is:\n\n" + GOOD + "\n\nHope that helps.", "auto-approve"),
    ("numbers as strings", STRINGY, "auto-approve"),
    ("null line_items", NULLITEMS, "auto-approve"),
    ("thousands separators", SEPARATORS, "needs-approval"),
]

SCRIPTS = {name: [reply] for name, reply, _ in ROBUSTNESS}
SCRIPTS["retry"] = ["not json at all", GOOD]     # 1st invalid -> client retries -> ok
SCRIPTS["garbage"] = ['{"foo": 1}', '{"foo": 2}']  # never invoice-shaped -> raises


class MockModel(BaseHTTPRequestHandler):
    scenario = "good"
    calls = 0

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = self.rfile.read(int(self.headers.get("Content-Length", 0)))  # noqa: F841
        replies = SCRIPTS[MockModel.scenario]
        content = replies[min(MockModel.calls, len(replies) - 1)]
        MockModel.calls += 1
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_contract():
    srv = HTTPServer(("127.0.0.1", 0), MockModel)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    iw.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/v1"
    iw.API_KEY, iw.MODEL = "test", "mock"
    raw = open(os.path.join(HERE, "sample_invoices", "acme_hardware.txt")).read()

    # robustness: each messy-but-valid reply must parse on the FIRST call
    for name, _, expected in ROBUSTNESS:
        MockModel.scenario, MockModel.calls = name, 0
        d = iw.decide(iw.extract_via_llm(raw))
        assert d["route"] == expected and MockModel.calls == 1, (name, d, MockModel.calls)
        print(f"CONTRACT ok — {name:<22}-> {expected} (1 call)")

    # retry: first reply invalid, client re-asks, second is valid
    MockModel.scenario, MockModel.calls = "retry", 0
    d = iw.decide(iw.extract_via_llm(raw))
    assert d["route"] == "auto-approve" and MockModel.calls == 2, d
    print("CONTRACT ok — malformed reply-> retried, then parsed (2 calls)")

    # garbage: model never returns valid JSON -> pipeline raises, driver holds
    MockModel.scenario, MockModel.calls = "garbage", 0
    try:
        iw.extract_via_llm(raw)
        raise AssertionError("expected ValueError on persistent garbage")
    except ValueError:
        print("CONTRACT ok — garbage reply  -> raises, invoice would be held")
    srv.shutdown()


if __name__ == "__main__":
    iw.banner()
    print("  " + iw._c("2", "tests · pipeline (golden) + LLM client contract (mock)\n"))
    test_golden()
    test_contract()
    print("\n" + iw._c("32", "ALL TESTS PASSED"))
