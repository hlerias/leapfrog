#!/usr/bin/env python3
"""
Leapfrog Lab Bench - a small branded web interface for the labs.

    python leapfrog_web.py            then open http://localhost:8000

No pip install. No admin rights. No internet needed. Python 3.8+ only.
Talks to whatever OpenAI-compatible endpoint you point it at - by default
a local Ollama:  ollama serve  +  ollama pull llama3.2
"""

import json, os, re, sys, threading, time, urllib.request, webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE  = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
KEY   = os.getenv("LLM_API_KEY", "ollama")
MODEL = os.getenv("LLM_MODEL", "llama3.2")
PORT  = int(os.getenv("PORT", "8000"))
RUNS  = 3

# ---------------------------------------------------------------- model call
def ask(prompt, timeout=120):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(BASE.rstrip("/") + "/chat/completions", data=body,
          headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["choices"][0]["message"]["content"]

def model_alive():
    try:
        t0 = time.time(); ask("say ok", timeout=20); return True, round(time.time() - t0, 1)
    except Exception as e:
        return False, str(e)

def first_int(s):
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group(0)) if m else None

# ---------------------------------------------------------------- lab 10
TASKS10 = [
    ("sentiment",    "One word, positive or negative: the flight was delayed four hours and nobody told us.",
                     lambda a: "negativ" in a.lower()),
    ("count 'r's",   "How many times does the letter r appear in the word strawberry? Reply with the number only.",
                     lambda a: first_int(a) == 3),
    ("extract date", "Extract the date from: invoice dated 14 March 2026. Reply YYYY-MM-DD only.",
                     lambda a: "2026-03-14" in a),
    ("days between", "How many days from 2026-03-14 to 2026-04-02? Reply with the number only.",
                     lambda a: first_int(a) == 19),
    ("classify",     "Broken laptop screen: which team, IT or Legal? One word.",
                     lambda a: a.strip().lower().strip(".") == "it"),
    ("multiply",     "What is 37 * 46? Reply with the number only.",
                     lambda a: first_int(a) == 1702),
]

def run_lab10(emit):
    emit("note", {"text": "Six tasks that look equally easy. Each runs %d times." % RUNS})
    ok, info = model_alive()
    if not ok:
        emit("fail", {"text": "No model answering at %s" % BASE,
                      "fix": "ollama serve   +   ollama pull llama3.2", "detail": str(info)})
        return
    total = len(TASKS10) * RUNS
    emit("note", {"text": "%s is alive (%ss per call). %d calls to go - about %ds."
                  % (MODEL, info, total, int(float(info) * total))})
    rows = []
    for name, prompt, check in TASKS10:
        emit("task", {"name": name, "runs": RUNS})
        hits = 0
        for i in range(RUNS):
            try:
                good = bool(check(ask(prompt)))
            except Exception:
                good = False
            hits += good
            emit("dot", {"name": name, "i": i, "ok": good})
        verdict = "inside" if hits == RUNS else ("jagged" if hits else "outside")
        rows.append((name, hits, verdict))
        emit("row", {"name": name, "hits": hits, "runs": RUNS, "verdict": verdict})
    good = [n for n, h, v in rows if v == "inside"]
    bad  = [n for n, h, v in rows if v != "inside"]
    emit("done", {"trust": good, "avoid": bad,
                  "text": "Same shape of task, different reliability. The rows to fear are the "
                          "2/3 ones - reliably wrong is easy to catch, sometimes right is what ships."})

# ---------------------------------------------------------------- lab 11
RELIABLE = {"sentiment": True, "classify": True, "extract": True,
            "count": False, "days_between": False, "multiply": False}
CODE = {
    "count":        lambda p: str(p[1].count(p[0])),
    "days_between": lambda p: str((date.fromisoformat(p[1]) - date.fromisoformat(p[0])).days),
    "multiply":     lambda p: str(p[0] * p[1]),
}
PROMPT = {
    "sentiment": lambda p: "One word, positive or negative: " + p,
    "classify":  lambda p: "Which team handles this, IT or Legal? One word: " + p,
    "extract":   lambda p: "Extract the date, reply YYYY-MM-DD only: " + p,
}
TASKS11 = [
    ("sentiment",    "the flight was delayed four hours and nobody told us"),
    ("count",        ("r", "strawberry")),
    ("classify",     "my laptop screen is cracked"),
    ("days_between", ("2026-03-14", "2026-04-02")),
    ("extract",      "invoice dated 14 March 2026"),
    ("multiply",     (37, 46)),
]

def run_lab11(emit):
    emit("note", {"text": "Lab 10's map, turned into a routing rule. Watch the route column."})
    up, info = model_alive()
    if not up:
        emit("note", {"text": "Model not running - the code-routed rows still answer. "
                              "For the rest: ollama serve + ollama pull llama3.2"})
    calls = coded = 0
    for kind, payload in TASKS11:
        if RELIABLE[kind]:
            if up:
                try:
                    answer = ask(PROMPT[kind](payload)).strip(); calls += 1
                except Exception:
                    answer = "(model call failed)"
            else:
                answer = "(needs the model)"
            route = "model"
        else:
            answer = CODE[kind](payload); coded += 1
            route = "code"
        emit("route", {"task": kind, "route": route, "answer": answer})
    emit("done", {"calls": calls, "coded": coded, "total": len(TASKS11),
                  "text": "The model did not get smarter. It stopped being asked to do what code "
                          "already does perfectly - and cost, latency and error rate all fell at once."})

LABS = {
    "10": ("Map the jagged frontier", "Ch 3 &middot; 9", run_lab10,
           "Give your model six tasks that look equally easy. Find the ones it quietly gets wrong."),
    "11": ("Route around the jag", "Ch 6 &middot; 10", run_lab11,
           "Language to the model, arithmetic to plain code. Half the calls, no wrong answers."),
}

# ---------------------------------------------------------------- the page
MOTIF = '''<svg viewBox="0 0 380 230" fill="none" xmlns="http://www.w3.org/2000/svg" class="motif">
<defs><linearGradient id="acc" x1="0" y1="230" x2="380" y2="0" gradientUnits="userSpaceOnUse">
<stop stop-color="#34e0e0"/><stop offset="1" stop-color="#7c8bff"/></linearGradient></defs>
<rect x="36" y="150" width="20" height="60" rx="5" fill="rgba(255,255,255,0.10)"/>
<rect x="106" y="120" width="20" height="90" rx="5" fill="rgba(255,255,255,0.13)"/>
<rect x="176" y="90" width="20" height="120" rx="5" fill="rgba(255,255,255,0.16)"/>
<rect x="246" y="120" width="20" height="90" rx="5" fill="rgba(124,139,255,0.30)"/>
<rect x="316" y="150" width="20" height="60" rx="5" fill="rgba(52,224,224,0.34)"/>
<rect x="20" y="209" width="340" height="2" rx="1" fill="rgba(255,255,255,0.14)"/>
<path d="M24 196 C 96 40, 250 10, 356 150" stroke="#7fe7e0" stroke-width="12" stroke-linecap="round" fill="none" opacity="0.10"/>
<path d="M24 196 C 96 40, 250 10, 356 150" stroke="url(#acc)" stroke-width="5.5" stroke-linecap="round" fill="none"/>
<circle cx="182" cy="30" r="26" fill="#34e0e0" opacity="0.10"/>
<circle cx="182" cy="30" r="12" fill="#0e1330" stroke="url(#acc)" stroke-width="4"/></svg>'''

PAGE = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Leapfrog &middot; Lab Bench</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--cy:#34e0e0;--vi:#7c8bff;--lv:#aebbe6;--ink:#eef4ff;--line:rgba(255,255,255,.14)}
body{min-height:100vh;background:radial-gradient(120% 80% at 50% 26%,#1b2350 0%,#0e1330 46%,#080b1f 100%);
 background-attachment:fixed;color:var(--ink);
 font-family:Poppins,"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 padding:34px 20px 60px}
.wrap{max-width:900px;margin:0 auto}
.frame{border:1px solid var(--line);border-radius:18px;padding:34px 30px 30px;position:relative;overflow:hidden}
.hero{display:flex;align-items:center;gap:26px;flex-wrap:wrap}
.motif{width:150px;height:91px;flex:none}
.kicker{font-weight:600;font-size:10.5px;letter-spacing:.42em;color:#7fe7e0;text-transform:uppercase}
h1{font-weight:800;font-size:38px;letter-spacing:-.02em;line-height:1;margin:7px 0 9px}
.rule{width:52px;height:3px;border-radius:2px;background:linear-gradient(90deg,var(--cy),var(--vi));margin-bottom:11px}
.sub{font-size:14.5px;color:rgba(255,255,255,.72);line-height:1.55;max-width:430px}
.status{display:inline-flex;align-items:center;gap:8px;margin-top:20px;padding:7px 14px;border:1px solid var(--line);
 border-radius:999px;font-size:12.5px;color:var(--lv);background:rgba(255,255,255,.03)}
.pip{width:8px;height:8px;border-radius:50%;background:#6b7280}
.pip.on{background:var(--cy);box-shadow:0 0 10px var(--cy)}.pip.off{background:#ff8a5c}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px}
.card{border:1px solid var(--line);border-radius:14px;padding:20px;background:rgba(255,255,255,.03);
 transition:border-color .2s,transform .2s}
.card:hover{border-color:rgba(52,224,224,.42);transform:translateY(-2px)}
.chip{display:inline-block;font-size:10.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
 color:#08122a;background:linear-gradient(90deg,var(--cy),var(--vi));padding:3px 9px;border-radius:5px}
.card h3{font-size:17px;font-weight:700;margin:11px 0 7px}
.card p{font-size:13.5px;color:var(--lv);line-height:1.55;margin-bottom:15px}
button{font-family:inherit;font-weight:600;font-size:13.5px;cursor:pointer;border:none;border-radius:9px;
 padding:10px 18px;color:#08122a;background:linear-gradient(90deg,var(--cy),var(--vi))}
button:disabled{opacity:.45;cursor:default}
.console{margin-top:24px;border:1px solid var(--line);border-radius:14px;background:rgba(4,6,18,.62);
 padding:18px 20px;min-height:120px;font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
 font-size:12.7px;line-height:1.85;color:var(--lv);white-space:pre-wrap;word-break:break-word}
.console .muted{color:rgba(174,187,230,.55)}
.console .cy{color:var(--cy)}.console .vi{color:var(--vi)}
.console .am{color:#ffb450}.console .rd{color:#ff7878}.console .ink{color:var(--ink)}
.console b{color:var(--ink);font-weight:600}
.foot{margin-top:22px;font-size:12px;color:rgba(255,255,255,.4);text-align:center}
.foot a{color:var(--lv)}
@media(max-width:720px){.grid{grid-template-columns:1fr}h1{font-size:30px}}
</style></head><body><div class="wrap"><div class="frame">
  <div class="hero">__MOTIF__
    <div><div class="kicker">A Field Guide</div><h1>Lab Bench</h1><div class="rule"></div>
    <p class="sub">Two labs from <b>Leapfrog</b>, running against a model on your own machine.
    Nothing leaves this computer.</p></div>
  </div>
  <div class="status"><span class="pip" id="pip"></span><span id="stat">checking your model&hellip;</span></div>
  <div class="grid">__CARDS__</div>
  <div class="console" id="con"><span class="muted">Pick a lab above. Output appears here, live.</span></div>
  <div class="foot">LEAPFROG &middot; the free field guide &mdash; <a href="https://leapfrog.lerias.org">leapfrog.lerias.org</a></div>
</div></div>
<script>
const con=document.getElementById('con');
function line(html){con.insertAdjacentHTML('beforeend',html+'\\n');con.scrollTop=con.scrollHeight;}
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
fetch('/api/status').then(r=>r.json()).then(d=>{
  document.getElementById('pip').className='pip '+(d.ok?'on':'off');
  document.getElementById('stat').textContent=d.ok
    ? d.model+' is running \\u00b7 '+d.secs+'s per call'
    : 'no model at '+d.base+' \\u2014 run: ollama serve';
});
let busy=false;
function run(lab){
  if(busy)return; busy=true;
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  con.innerHTML='';
  const es=new EventSource('/api/run?lab='+lab);
  let open=false;
  es.addEventListener('note',e=>line('<span class="muted">'+esc(JSON.parse(e.data).text)+'</span>'));
  es.addEventListener('fail',e=>{const d=JSON.parse(e.data);
    line('<span class="rd">'+esc(d.text)+'</span>');
    line('<span class="muted">Free fix: </span><span class="cy">'+esc(d.fix)+'</span>');
    line('<span class="muted">'+esc(d.detail)+'</span>');});
  es.addEventListener('task',e=>{const d=JSON.parse(e.data);
    con.insertAdjacentHTML('beforeend','  '+esc(d.name).padEnd(14,'\\u00a0')+' <span id="d-'+esc(d.name).replace(/\\W/g,'')+'"></span>');
    open=true;});
  es.addEventListener('dot',e=>{const d=JSON.parse(e.data);
    const el=document.getElementById('d-'+esc(d.name).replace(/\\W/g,''));
    if(el)el.insertAdjacentHTML('beforeend',d.ok?'<span class="cy">\\u25cf</span>':'<span class="muted">\\u25cb</span>');});
  es.addEventListener('row',e=>{const d=JSON.parse(e.data);
    const v={inside:'<span class="ink">inside the frontier</span>',
             jagged:'<span class="am">JAGGED \\u2014 sometimes right</span>',
             outside:'<span class="rd">OUTSIDE \\u2014 reliably wrong</span>'}[d.verdict];
    line('  '+d.hits+'/'+d.runs+'  '+v); open=false;});
  es.addEventListener('route',e=>{const d=JSON.parse(e.data);
    const r=d.route==='code'?'<span class="cy">code&nbsp;</span>':'<span class="vi">model</span>';
    line('  '+esc(d.task).padEnd(14,'\\u00a0')+r+'  '+esc(d.answer));});
  es.addEventListener('done',e=>{const d=JSON.parse(e.data);
    line('');
    if(d.trust)line('  <span class="muted">trust it for :</span> <span class="cy">'+esc(d.trust.join(', ')||'nothing here')+'</span>');
    if(d.avoid)line('  <span class="muted">do NOT       :</span> <span class="am">'+esc(d.avoid.join(', ')||'nothing')+'</span>');
    if(d.total)line('  <span class="muted">'+d.total+' tasks \\u00b7 </span><span class="vi">'+d.calls+' model calls</span><span class="muted"> \\u00b7 </span><span class="cy">'+d.coded+' answered by code</span>');
    line(''); line('  <b>What you just saw:</b> <span class="muted">'+esc(d.text)+'</span>');
    es.close(); busy=false;
    document.querySelectorAll('button').forEach(b=>b.disabled=false);});
  es.onerror=()=>{es.close();busy=false;
    document.querySelectorAll('button').forEach(b=>b.disabled=false);};
}
</script></body></html>'''

def page():
    cards = ""
    for lab, (title, chip, _fn, blurb) in LABS.items():
        cards += ('<div class="card"><span class="chip">Lab %s &middot; %s</span><h3>%s</h3><p>%s</p>'
                  '<button onclick="run(\'%s\')">Run it &rarr;</button></div>' % (lab, chip, title, blurb, lab))
    return PAGE.replace("__MOTIF__", MOTIF).replace("__CARDS__", cards)

# ---------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the terminal clean
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self._send(200, "text/html; charset=utf-8", page().encode())
        elif self.path.startswith("/api/status"):
            ok, info = model_alive()
            self._send(200, "application/json",
                       json.dumps({"ok": ok, "model": MODEL, "base": BASE,
                                   "secs": info if ok else None}).encode())
        elif self.path.startswith("/api/run"):
            lab = "10"
            if "lab=" in self.path:
                lab = self.path.split("lab=")[1].split("&")[0]
            if lab not in LABS:
                self._send(404, "text/plain", b"no such lab"); return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def emit(event, data):
                try:
                    self.wfile.write(("event: %s\ndata: %s\n\n" % (event, json.dumps(data))).encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    raise SystemExit
            try:
                LABS[lab][2](emit)
            except SystemExit:
                pass
            except Exception as e:
                try:
                    emit("fail", {"text": "Lab crashed", "fix": "check the terminal", "detail": str(e)})
                except Exception:
                    pass
        else:
            self._send(404, "text/plain", b"not found")

def main():
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        print("\n  Port %d is already busy on this machine." % PORT)
        print("  Pick another one:  \033[38;2;52;224;224mPORT=8001 python leapfrog_web.py\033[0m")
        print("  (detail: %s)\n" % e)
        raise SystemExit(1)
    url = "http://localhost:%d" % PORT
    print("\n  \033[38;2;52;224;224m\u25cf\033[0m  LEAPFROG \u00b7 Lab Bench")
    print("     open %s   (ctrl-c to stop)" % url)
    print("     model: %s at %s\n" % (MODEL, BASE))
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("  stopped.\n")

if __name__ == "__main__":
    main()
