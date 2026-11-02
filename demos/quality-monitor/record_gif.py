# Leapfrog Labs · https://leapfrog.lerias.org · code MIT licensed
# ────────────────────────────────────────────────────────────
# Record this demo as an animated GIF (optional — needs Pillow)
#
# WHAT IT IS    The GIF in README.md, made reproducible. It runs the REAL
#               commands in a pseudo-terminal, so colours come through as a
#               user sees them, then draws the output frame by frame.
# HOW IT WORKS  1) run each command and capture its output
#               2) type the command, scroll the output in, hold on the lines
#                  worth reading   3) save every frame into one GIF
# PROOF POINT   Every number in the GIF is the program's own output. If the
#               demo changes, re-record and the GIF changes with it.
#
# Run:  pip install pillow
#       python demos/quality-monitor/record_gif.py              (short cut → demo.gif)
#       python demos/quality-monitor/record_gif.py --full out.gif
#
# Linux or macOS (it uses a pseudo-terminal). Fonts: DejaVu Sans Mono, with
# Noto Sans Mono CJK for the circled step numbers if present.
import os
import pty
import re
import select
import subprocess
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("record_gif.py needs Pillow:  pip install pillow")

DEMO = os.path.dirname(os.path.abspath(__file__))
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = _args[0] if _args else os.path.join(DEMO, "demo.gif")
FRAMES_DIR = None

# --- scenes: (command shown, argv, holds) -----------------------------------
# holds: substring -> ms to hold once that line has appeared
SCENES = [
    ("python3 quality_monitor.py --guard", [sys.executable, "-I", "quality_monitor.py", "--guard"], {
        "All green.": 3500, "scored ": 1500, "  offsites ": 300,
        "ALERT  travel    day 7": 2500, "error rate over 2%": 4000,
        "CHANGED": 2500, "It isn't the model": 5000,
        "stopped ": 2500,
    }),
    ("python3 test_monitor.py", [sys.executable, "-I", "test_monitor.py"], {
        "ALL TESTS PASSED": 4000,
    }),
]

SHORT = [
    ("python3 quality_monitor.py --guard --brief", [sys.executable, "-I", "quality_monitor.py", "--guard", "--brief"], {
        "All green.": 3500, "ALERT  travel    day 7": 2500, "error rate over 2%": 4000,
        "CHANGED": 2500, "It isn't the model": 5000, "oncall    from day 4": 4000,
    }),
]
if "--full" not in sys.argv:
    SCENES = SHORT

COLS, ROWS = 100, 34
FONT_SIZE = 15
PAD_X, PAD_Y, BAR_H = 18, 14, 34
LINE_MS, BLANK_MS, TYPE_MS = 70, 30, 45

THEME = {
    "bg": (13, 17, 23), "bar": (30, 35, 43), "fg": (230, 237, 243),
    "dim": (139, 148, 158), "prompt": (63, 185, 80),
    31: (255, 123, 114), 32: (63, 185, 80), 33: (210, 153, 34),
    36: (57, 197, 207), 96: (86, 212, 221),
}
XTERM = {44: (0, 215, 215), 99: (167, 139, 250)}   # 38;5;n used by the demos

def _font(*names):
    """First font file found in the usual places, else None."""
    dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/Library/Fonts"), "/Library/Fonts"]
    for d in dirs:
        for root, _, files in os.walk(d):
            for n in names:
                if n in files:
                    return os.path.join(root, n)
    return None


MONO = _font("DejaVuSansMono.ttf")
MONO_B = _font("DejaVuSansMono-Bold.ttf") or MONO
CJK = _font("NotoSansCJK-Regular.ttc") or MONO
CJK_B = _font("NotoSansCJK-Bold.ttc") or CJK
if not MONO:
    raise SystemExit("record_gif.py needs the DejaVu Sans Mono font (e.g. apt install fonts-dejavu-core)")


def cjk_mono(path):
    for i in range(12):
        try:
            f = ImageFont.truetype(path, FONT_SIZE, index=i)
        except OSError:
            break
        if "Mono" in f.getname()[0]:
            return f
    return ImageFont.truetype(path, FONT_SIZE)


F = {False: ImageFont.truetype(MONO, FONT_SIZE), True: ImageFont.truetype(MONO_B, FONT_SIZE)}
FB = {False: cjk_mono(CJK), True: cjk_mono(CJK_B)}
CW = round(F[False].getlength("M"))
LH = round(FONT_SIZE * 1.32)
W = PAD_X * 2 + COLS * CW
H = BAR_H + PAD_Y * 2 + ROWS * LH


# --- capture: run in a pty so isatty() is true and colours are emitted ------
def capture(argv):
    master, slave = pty.openpty()
    env = dict(os.environ, TERM="xterm-256color", COLUMNS=str(COLS))
    env.pop("NO_COLOR", None)
    p = subprocess.Popen(argv, cwd=DEMO, stdout=slave, stderr=slave, env=env, close_fds=True)
    os.close(slave)
    buf = b""
    while True:
        r, _, _ = select.select([master], [], [], 0.2)
        if r:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                chunk = b""
            if not chunk:
                break
            buf += chunk
        elif p.poll() is not None:
            break
    p.wait()
    os.close(master)
    return buf.decode("utf-8").replace("\r\n", "\n"), p.returncode


SGR = re.compile(r"\x1b\[([0-9;]*)m")


def parse(text):
    """-> list of lines; each line a list of (text, fg, bold)."""
    lines, cur = [], []
    fg, bold, dim = None, False, False
    pos = 0
    for m in SGR.finditer(text + "\x1b[0m"):
        seg = text[pos:m.start()]
        for i, part in enumerate(seg.split("\n")):
            if i:
                lines.append(cur)
                cur = []
            if part:
                color = fg or (THEME["dim"] if dim else THEME["fg"])
                if dim and fg:
                    color = tuple(int(c * 0.75) for c in fg)
                cur.append((part, color, bold))
        codes = [int(c) for c in (m.group(1) or "0").split(";") if c != ""] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                fg, bold, dim = None, False, False
            elif c == 1:
                bold = True
            elif c == 2:
                dim = True
            elif c == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
                fg = XTERM.get(codes[i + 2], THEME["fg"])
                i += 2
            elif c in THEME:
                fg = THEME[c]
            i += 1
        pos = m.end()
    if cur:
        lines.append(cur)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def wrap(line):
    """Soft-wrap a styled line at COLS, like a terminal does."""
    out, cur, n = [], [], 0
    for text, color, bold in line:
        while text:
            room = COLS - n
            if room == 0:
                out.append(cur)
                cur, n = [], 0
                room = COLS
            piece, text = text[:room], text[room:]
            cur.append((piece, color, bold))
            n += len(piece)
    out.append(cur)
    return out


def plain(line):
    return "".join(t for t, _, _ in line)


# --- rendering ----------------------------------------------------------------
def draw_frame(rows, cursor=None):
    img = Image.new("RGB", (W, H), THEME["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, BAR_H], fill=THEME["bar"])
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 20 + i * 20
        d.ellipse([cx - 6, BAR_H // 2 - 6, cx + 6, BAR_H // 2 + 6], fill=col)
    title = "leapfrog/demos/quality-monitor"
    d.text(((W - F[False].getlength(title)) / 2, BAR_H // 2 - FONT_SIZE // 2 - 1), title,
           font=F[False], fill=THEME["dim"])
    y = BAR_H + PAD_Y
    for row in rows[-ROWS:]:
        x = PAD_X
        for text, color, bold in row:
            for ch in text:
                if ch in "①②③④⑤⑥":                 # wide glyph: give it two cells
                    d.text((x, y), ch, font=FB[bold], fill=color)
                    x += 2 * CW
                    continue
                if ch != " ":
                    d.text((x, y), ch, font=F[bold], fill=color)
                x += CW
        y += LH
    if cursor:
        cx, cy = cursor
        d.rectangle([PAD_X + cx * CW, BAR_H + PAD_Y + cy * LH + 2,
                     PAD_X + cx * CW + CW - 2, BAR_H + PAD_Y + cy * LH + LH - 2], fill=THEME["fg"])
    return img


frames, durations = [], []


def emit(rows, ms, cursor=None):
    frames.append(draw_frame(rows, cursor))
    durations.append(ms)


def prompt_line(cmd_typed):
    return [("$ ", THEME["prompt"], True), (cmd_typed, THEME["fg"], False)]


def cursor_at(screen, col):
    shown = screen[-ROWS:]
    return (col, len(shown) - 1)


screen = []
results = []
for idx, (cmd, argv, holds) in enumerate(SCENES):
    out, code = capture(argv)
    results.append((cmd, code, out))
    # type the command
    screen.append(prompt_line(""))
    emit(screen, 700 if idx == 0 else 500, cursor_at(screen, 2))
    for k in range(1, len(cmd) + 1, 2):
        screen[-1] = prompt_line(cmd[:k])
        emit(screen, TYPE_MS * 2, cursor_at(screen, 2 + k))
    screen[-1] = prompt_line(cmd)
    emit(screen, 500, cursor_at(screen, 2 + len(cmd)))
    # stream the output
    for line in parse(out):
        for row in wrap(line):
            screen.append(row)
            text = plain(row)
            ms = BLANK_MS if not text.strip() else LINE_MS
            for key, hold in holds.items():
                if key in text:
                    ms = hold
            emit(screen, ms)
    screen.append([])
    screen.append([("$ ", THEME["prompt"], True)])
    emit(screen, 2000, cursor_at(screen, 2))
    if idx < len(SCENES) - 1:
        screen = []                        # clear the screen between scenes

# --- merge identical consecutive frames, then save ----------------------------
pal = Image.new("RGB", (W, H * 2), THEME["bg"])
pal.paste(max(frames, key=lambda f: len(f.getcolors(1 << 20) or [])), (0, 0))
pal.paste(frames[-1], (0, H))
palette = pal.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
q = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
q[0].save(OUT, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=True,
          disposal=1)

if FRAMES_DIR:
    os.makedirs(FRAMES_DIR, exist_ok=True)
    marks = {}
    for i, d in enumerate(durations):
        if d >= 2500:
            marks[i] = d
    for i in marks:
        frames[i].save(os.path.join(FRAMES_DIR, f"hold_{i:03d}.png"))

for cmd, code, _ in results:
    print(f"captured: {cmd!r:44} exit {code}")
print(f"frames: {len(frames)}  length: {sum(durations) / 1000:.1f}s  size: {os.path.getsize(OUT) / 1e6:.2f} MB  "
      f"{W}x{H}")
