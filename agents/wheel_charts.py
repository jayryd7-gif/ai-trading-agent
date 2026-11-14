"""
wheel_charts.py - Charts for the wheel paper account (SVG, no extra tools).

  paper-trading/wheel/value.svg     account profit / loss in CAD, day by day
  paper-trading/wheel/holdings.svg  each holding's profit / loss right now (CAD and %)

Same look as the dashboard's other charts (agents/charts.py).
"""

import os
from xml.sax.saxutils import escape

from charts import GRID, RIGHT, SUBTLE, TEXT, WRONG, _frame, _message

W = 640


def _pct(v):
    v = round(v, 1) + 0.0          # no "-0.0%"
    return f"{v:+.1f}%"


def _money(v):
    v = round(v) + 0
    return f"{'+' if v >= 0 else '-'}${abs(v):,.0f}"


def value_chart(history, fx, cur="CAD", start_label="$10,000 CAD"):
    """history: [{"date": "YYYY-MM-DD", "equity_usd": float}, ...]; start = first value."""
    h = 300
    if not history:
        return _frame(f"Account profit / loss ({cur})", "No runs yet", _message("Starts after the first run"))
    start = history[0].get("start_usd", history[0]["equity_usd"])
    pts = [(r["date"], (r["equity_usd"] - start) / fx) for r in history]
    lo, hi = min(0, *(p for _, p in pts)), max(0, *(p for _, p in pts))
    pad = max((hi - lo) * 0.15, 50)
    lo, hi = lo - pad, hi + pad
    left, right, top, bottom = 70, W - 30, 70, h - 40

    def x(i):
        return left + (right - left) * (i / max(len(pts) - 1, 1)) if len(pts) > 1 else (left + right) / 2

    def y(v):
        return bottom - (v - lo) / (hi - lo) * (bottom - top)

    body = []
    for v in sorted({lo + pad, 0, hi - pad}):
        dash = "" if v == 0 else 'stroke-dasharray="3 3"'
        body.append(f'<line x1="{left}" x2="{right}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
                    f'stroke="{GRID}" stroke-width="1" {dash}/>')
        body.append(f'<text x="{left - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" '
                    f'fill="{SUBTLE}">{_money(v)}</text>')
    last = pts[-1][1]
    color = RIGHT if last >= 0 else WRONG
    if len(pts) > 1:
        path = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(pts))
        body.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" '
                    f'stroke-linejoin="round" stroke-linecap="round"/>')
    body.append(f'<circle cx="{x(len(pts) - 1):.1f}" cy="{y(last):.1f}" r="4.5" fill="{color}" '
                f'stroke="#ffffff" stroke-width="2"/>')
    body.append(f'<text x="{min(x(len(pts) - 1) + 8, right - 4):.1f}" y="{y(last) - 10:.1f}" font-size="12" '
                f'font-weight="bold" text-anchor="{"end" if len(pts) > 1 else "start"}" fill="{TEXT}">'
                f'{_money(last)} {cur}</text>')
    if len(pts) > 1:
        body.append(f'<text x="{left}" y="{h - 16}" font-size="11" fill="{SUBTLE}">{pts[0][0]}</text>')
        body.append(f'<text x="{right}" y="{h - 16}" font-size="11" text-anchor="end" fill="{SUBTLE}">{pts[-1][0]}</text>')
    else:
        body.append(f'<text x="{x(0):.1f}" y="{h - 16}" font-size="11" text-anchor="middle" fill="{SUBTLE}">{pts[0][0]}</text>')
    pct = (history[-1]["equity_usd"] / start - 1) * 100
    return _frame(f"Account profit / loss ({cur})",
                  f"Started at {start_label} · now {_money(last)} {cur} ({_pct(pct)}) · {len(pts)} day(s) of trading",
                  "".join(body), height=h)


def holdings_chart(rows, cur="CAD"):
    """rows: [{"label": "SOFI put $14 (sold 11-16)", "pnl_cad": float, "pct": float}, ...]"""
    if not rows:
        return _frame("What it holds: profit / loss now", "Nothing open",
                      _message("No open positions"))
    bar_h, gap, top = 26, 12, 64
    h = top + len(rows) * (bar_h + gap) + 24
    left, right = 245, W - 135
    mid = (left + right) / 2
    biggest = max(max(abs(r["pnl_cad"]) for r in rows), 50)   # $50 floor: tiny moves stay tiny
    scale = (right - left) / 2 / biggest
    body = [f'<line x1="{mid}" x2="{mid}" y1="{top - 6}" y2="{h - 18}" stroke="{GRID}" stroke-width="1"/>']
    for i, r in enumerate(rows):
        yy = top + i * (bar_h + gap)
        v = r["pnl_cad"]
        wdt = max(abs(v) * scale, 2)
        x0 = mid if v >= 0 else mid - wdt
        color = RIGHT if v >= 0 else WRONG
        body.append(f'<text x="{left - 12}" y="{yy + bar_h / 2 + 4}" font-size="12" text-anchor="end" '
                    f'fill="{TEXT}">{escape(r["label"])}</text>')
        body.append(f'<rect x="{x0:.1f}" y="{yy}" width="{wdt:.1f}" height="{bar_h}" rx="4" fill="{color}"/>')
        body.append(f'<text x="{W - 20}" y="{yy + bar_h / 2 + 4}" font-size="12" font-weight="bold" '
                    f'text-anchor="end" fill="{TEXT}">{_money(v)} ({_pct(r["pct"])})</text>')
    total = sum(r["pnl_cad"] for r in rows)
    return _frame("What it holds: profit / loss now",
                  f"{len(rows)} open · together {_money(total)} {cur} · green = up, red = down",
                  "".join(body), height=h)


def save(folder, history, fx, rows, cur="CAD", start_label="$10,000 CAD"):
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, "value.svg"), "w").write(value_chart(history, fx, cur, start_label))
    open(os.path.join(folder, "holdings.svg"), "w").write(holdings_chart(rows, cur))
