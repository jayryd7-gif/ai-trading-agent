"""
charts.py - Draws the dashboard's charts as SVG images.

SVG is a picture made of text, so this needs no extra tools and costs nothing.
Each chart is saved in reports/charts/ and shown on DASHBOARD.md.

Charts:
  results-by-confidence.svg   Right / Wrong / Flat counts for High, Medium, Low
  running-hit-rate.svg        hit rate after each decisive call, vs 50%
  recent-sessions.svg         what price did in recent sessions, vs the lean
"""

import os
from xml.sax.saxutils import escape

CHART_FOLDER = os.path.join("reports", "charts")

RIGHT, WRONG, FLAT = "#2da44e", "#cf222e", "#8c959f"
CALM, MOVED = "#0969da", "#bf8700"
TEXT, SUBTLE, GRID = "#1f2328", "#656d76", "#d0d7de"
LEAN_ICON = {"Bullish": "▲", "Bearish": "▼", "Neutral": "◆"}
RESULT_COLOR = {"Right": RIGHT, "Wrong": WRONG, "Flat": FLAT,
                "Calm": CALM, "Moved": MOVED}


def _frame(title, subtitle, body, width=640, height=300):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="#ffffff" stroke="{GRID}"/>'
        f'<text x="20" y="28" font-size="16" font-weight="bold" fill="{TEXT}">{escape(title)}</text>'
        f'<text x="20" y="46" font-size="12" fill="{SUBTLE}">{escape(subtitle)}</text>'
        f'{body}</svg>'
    )


def _message(text):
    return (f'<text x="320" y="165" font-size="14" text-anchor="middle" '
            f'fill="{SUBTLE}">{escape(text)}</text>')


def _legend(items, y, x=20):
    out, cursor = [], x
    for color, label in items:
        out.append(f'<rect x="{cursor}" y="{y - 10}" width="12" height="12" rx="2" fill="{color}"/>')
        out.append(f'<text x="{cursor + 18}" y="{y}" font-size="12" fill="{SUBTLE}">{escape(label)}</text>')
        cursor += 28 + 7 * len(label)
    return "".join(out)


def _rate(rows):
    right = sum(1 for r in rows if r["result"] == "Right")
    wrong = sum(1 for r in rows if r["result"] == "Wrong")
    flat = sum(1 for r in rows if r["result"] == "Flat")
    return right, wrong, flat


def chart_by_confidence(scores):
    directional = [r for r in scores if r["bias"] in ("Bullish", "Bearish")]
    title = "Results by confidence"
    subtitle = "Bullish and Bearish calls only. Taller bars mean more calls."
    if not directional:
        return _frame(title, subtitle, _message("No directional calls scored yet"))

    levels = ("High", "Medium", "Low")
    counts = {lv: _rate([r for r in directional if r["confidence"] == lv]) for lv in levels}
    top = max(1, max(sum(c) for c in counts.values()))
    left, right_edge, base, ceiling = 70, 610, 235, 80
    scale = (base - ceiling) / top

    # Whole-number ticks with an even step (1, 2, 5, 10, ...), so labels never look uneven
    step = next(s for s in (1, 2, 5, 10, 20, 50, 100, 200, 500) if top / s <= 5)
    top = -(-top // step) * step          # round the top of the axis up to a tick
    scale = (base - ceiling) / top
    body = []
    for value in range(0, top + 1, step):
        y = base - value * scale
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right_edge}" y2="{y:.1f}" stroke="{GRID}"/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="{SUBTLE}">{value}</text>')

    slot = (right_edge - left) / 3
    for i, lv in enumerate(levels):
        right, wrong, flat = counts[lv]
        total = right + wrong + flat
        cx = left + slot * i + slot / 2
        y = base
        for value, color in ((right, RIGHT), (wrong, WRONG), (flat, FLAT)):
            if value == 0:
                continue
            h = value * scale
            y -= h
            body.append(f'<rect x="{cx - 40:.1f}" y="{y:.1f}" width="80" height="{h:.1f}" fill="{color}"/>')
            if h >= 16:
                body.append(f'<text x="{cx:.1f}" y="{y + h / 2 + 4:.1f}" font-size="12" '
                            f'text-anchor="middle" fill="#ffffff" font-weight="bold">{value}</text>')
        decisive = right + wrong
        hit = f"{right / decisive * 100:.0f}% hit rate" if decisive else "no decisive calls"
        body.append(f'<text x="{cx:.1f}" y="{base + 18}" font-size="13" text-anchor="middle" fill="{TEXT}">{lv} ({total})</text>')
        body.append(f'<text x="{cx:.1f}" y="{base + 33}" font-size="11" text-anchor="middle" fill="{SUBTLE}">{hit}</text>')
    body.append(_legend([(RIGHT, "Right"), (WRONG, "Wrong"), (FLAT, "Session ended flat")], 290, x=20))
    return _frame(title, subtitle, "".join(body))


def chart_running_hit_rate(scores):
    decisive = [r for r in scores if r["bias"] in ("Bullish", "Bearish")
                and r["result"] in ("Right", "Wrong")]
    decisive.sort(key=lambda r: (r["date"], r["time_ny"]))
    title = "Running hit rate"
    subtitle = "Share of decisive calls that were right, after each call. Needs 30+ calls to mean anything."
    if len(decisive) < 2:
        return _frame(title, subtitle, _message("Needs at least 2 decisive calls"))

    left, right_edge, top, base = 60, 610, 70, 240
    n = len(decisive)

    def x_at(i):
        return left + (right_edge - left) * (i / (n - 1))

    def y_at(pct):
        return base - (base - top) * pct / 100

    body = []
    for pct in (0, 25, 50, 75, 100):
        y = y_at(pct)
        dash = ' stroke-dasharray="5 4"' if pct == 50 else ""
        color = MOVED if pct == 50 else GRID
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right_edge}" y2="{y:.1f}" stroke="{color}"{dash}/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="{SUBTLE}">{pct}%</text>')
    body.append(f'<text x="{left + 8}" y="{y_at(50) - 5:.1f}" font-size="11" fill="{MOVED}">coin flip (50%)</text>')

    points, right = [], 0
    for i, row in enumerate(decisive):
        if row["result"] == "Right":
            right += 1
        points.append((x_at(i), y_at(right / (i + 1) * 100)))
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    body.append(f'<polyline points="{path}" fill="none" stroke="{RIGHT}" stroke-width="2.5"/>')
    for x, y in points:
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{RIGHT}"/>')
    body.append(f'<text x="{left}" y="{base + 18}" font-size="11" fill="{SUBTLE}">call 1</text>')
    body.append(f'<text x="{right_edge}" y="{base + 18}" font-size="11" text-anchor="end" fill="{SUBTLE}">call {n}</text>')
    body.append(f'<text x="{points[-1][0] - 6:.1f}" y="{points[-1][1] - 9:.1f}" font-size="12" '
                f'text-anchor="end" fill="{TEXT}" font-weight="bold">{right / n * 100:.0f}%</text>')
    return _frame(title, subtitle, "".join(body))


def _lean_marker(cx, cy, bias):
    """A small triangle (up/down) or diamond, drawn as a shape so it never
    depends on the viewer's fonts."""
    if bias == "Bullish":
        pts = [(cx, cy - 5), (cx - 5, cy + 4), (cx + 5, cy + 4)]
    elif bias == "Bearish":
        pts = [(cx - 5, cy - 4), (cx + 5, cy - 4), (cx, cy + 5)]
    else:
        pts = [(cx, cy - 5), (cx + 5, cy), (cx, cy + 5), (cx - 5, cy)]
    coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polygon points="{coords}" fill="{TEXT}"/>'


def chart_recent_sessions(scores):
    recent = scores[-20:]
    title = "Recent sessions: what price did vs the lean"
    subtitle = "Bar = session move in percent. Color = result. Marker under each bar = the lean."
    if not recent:
        return _frame(title, subtitle, _message("No scored sessions yet"))

    left, right_edge, top, base = 60, 620, 70, 232
    biggest = max(0.1, max(abs(float(r["move_pct"])) for r in recent))
    mid = (top + base) / 2
    scale = (base - top) / 2 / biggest * 0.92

    body = [f'<line x1="{left}" y1="{mid:.1f}" x2="{right_edge}" y2="{mid:.1f}" stroke="{SUBTLE}"/>']
    for value in (biggest, -biggest):
        y = mid - value * scale
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right_edge}" y2="{y:.1f}" stroke="{GRID}" stroke-dasharray="3 3"/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="{SUBTLE}">{value:+.2f}%</text>')
    body.append(f'<text x="{left - 8}" y="{mid + 4:.1f}" font-size="11" text-anchor="end" fill="{SUBTLE}">0</text>')

    slot = (right_edge - left) / max(len(recent), 8)
    width = min(26, slot * 0.7)
    for i, row in enumerate(recent):
        move = float(row["move_pct"])
        cx = left + slot * i + slot / 2
        h = abs(move) * scale
        y = mid - h if move >= 0 else mid
        color = RESULT_COLOR.get(row["result"], FLAT)
        body.append(f'<rect x="{cx - width / 2:.1f}" y="{y:.1f}" width="{width:.1f}" height="{max(h, 1.5):.1f}" fill="{color}"/>')
        market = "N" if row["instrument"] == "nasdaq" else "G"
        body.append(_lean_marker(cx, base + 14, row["bias"]))
        body.append(f'<text x="{cx:.1f}" y="{base + 32}" font-size="10" text-anchor="middle" fill="{SUBTLE}">{market}</text>')
    body.append(_legend([(RIGHT, "Right"), (WRONG, "Wrong"), (FLAT, "Flat"),
                         (CALM, "Calm"), (MOVED, "Moved")], 292, x=20))
    # marker key, drawn with shapes
    x = 26
    for bias, label in (("Bullish", "Bullish"), ("Bearish", "Bearish"), ("Neutral", "Neutral")):
        body.append(_lean_marker(x, 308, bias))
        body.append(f'<text x="{x + 12}" y="312" font-size="12" fill="{SUBTLE}">{label}</text>')
        x += 86
    body.append(f'<text x="{right_edge}" y="312" font-size="11" text-anchor="end" fill="{SUBTLE}">N = Nasdaq, G = gold</text>')
    return _frame(title, subtitle, "".join(body), height=326)


def make_charts(scores):
    """Write all charts. Returns a list of (alt text, relative file path)."""
    os.makedirs(CHART_FOLDER, exist_ok=True)
    charts = [
        ("Results by confidence", "results-by-confidence.svg", chart_by_confidence),
        ("Running hit rate", "running-hit-rate.svg", chart_running_hit_rate),
        ("Recent sessions", "recent-sessions.svg", chart_recent_sessions),
    ]
    made = []
    for alt, name, builder in charts:
        path = os.path.join(CHART_FOLDER, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(builder(scores))
        made.append((alt, path.replace(os.sep, "/")))
    return made
