"""
crypto_charts.py - SVG charts for the crypto dashboard (no extra tools needed).

  value_chart      each bot's value over time, with the rotation bot's buys
                   and sells marked along the bottom
  holdings_chart   which coins the rotation bot held, and on which days
  drawdown_chart   how far each bot was below its own high, day by day
"""

from xml.sax.saxutils import escape

TEXT, SUBTLE, GRID = "#1f2328", "#656d76", "#d0d7de"
BUY, SELL, HELD, LIVE = "#2da44e", "#cf222e", "#2da44e", "#8250df"
LINE_COLORS = ["#0969da", "#bf8700", "#8c959f"]
WIDTH = 760


def _frame(title, subtitle, body, height):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" font-family="Helvetica, Arial, sans-serif">'
            f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="8" '
            f'fill="#ffffff" stroke="{GRID}"/>'
            f'<text x="20" y="28" font-size="16" font-weight="bold" fill="{TEXT}">{escape(title)}</text>'
            f'<text x="20" y="46" font-size="12" fill="{SUBTLE}">{escape(subtitle)}</text>'
            f'{body}</svg>')


def _legend(items, y, x=20):
    out, cursor = [], x
    for color, label, dashed in items:
        style = ' stroke-dasharray="4 3"' if dashed else ""
        out.append(f'<line x1="{cursor}" y1="{y - 4}" x2="{cursor + 18}" y2="{y - 4}" '
                   f'stroke="{color}" stroke-width="3"{style}/>')
        out.append(f'<text x="{cursor + 24}" y="{y}" font-size="12" fill="{SUBTLE}">{escape(label)}</text>')
        cursor += 40 + 7 * len(label)
    return "".join(out)


def _nice_step(span):
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000):
        if span / step <= 6:
            return step
    return 20000


def _x_axis(dates, x_of, base, left, right):
    """Month labels (every 3 months, or 6 for long periods)."""
    out, seen = [], set()
    every = 6 if (dates[-1] - dates[0]).days > 3 * 365 else 3
    for d in dates:
        key = (d.year, d.month)
        if d.day == 1 and (d.month - 1) % every == 0 and key not in seen:
            seen.add(key)
            x = x_of(d)
            out.append(f'<line x1="{x:.1f}" y1="{base}" x2="{x:.1f}" y2="{base + 4}" stroke="{SUBTLE}"/>')
            out.append(f'<text x="{x:.1f}" y="{base + 17}" font-size="11" text-anchor="middle" '
                       f'fill="{SUBTLE}">{d:%b %Y}</text>')
    return "".join(out)


def _go_live_marker(go_live, dates, x_of, top, base):
    if not dates or not (dates[0] <= go_live <= dates[-1]):
        return ""
    x = x_of(go_live)
    return (f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{base}" stroke="{LIVE}" '
            f'stroke-dasharray="5 4"/>'
            f'<text x="{x - 4:.1f}" y="{top + 12}" font-size="11" text-anchor="end" '
            f'fill="{LIVE}">paper trading starts →</text>')


def value_chart(series, start_cash, go_live, rotation_trades):
    """series: {name: [(date, value), ...]}"""
    names = list(series)
    dates = [d for d, _ in series[names[0]]]
    values = [v for s in series.values() for _, v in s]
    lo, hi = min(values + [start_cash]), max(values + [start_cash])
    step = _nice_step(hi - lo)
    lo, hi = (lo // step) * step, -(-hi // step) * step
    left, right, top, base = 70, WIDTH - 20, 70, 300
    x_of = lambda d: left + (d - dates[0]).days / max(1, (dates[-1] - dates[0]).days) * (right - left)
    y_of = lambda v: base - (v - lo) / (hi - lo) * (base - top)
    body = []
    v = lo
    while v <= hi + 0.01:
        y = y_of(v)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{GRID}"/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end" '
                    f'fill="{SUBTLE}">${v:,.0f}</text>')
        v += step
    y = y_of(start_cash)
    body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{SUBTLE}" '
                f'stroke-dasharray="2 3"/>')
    body.append(_x_axis(dates, x_of, base, left, right))
    body.append(_go_live_marker(go_live, dates, x_of, top, base))
    for color, name in zip(LINE_COLORS, names):
        pts = " ".join(f"{x_of(d):.1f},{y_of(val):.1f}" for d, val in series[name])
        body.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    # buys and sells of the rotation bot, as ticks under the axis
    for t in rotation_trades:
        x = x_of(t["date"])
        color = BUY if t["action"] == "Buy" else SELL
        y0 = base + 24 if t["action"] == "Buy" else base + 34
        body.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + 8}" stroke="{color}" stroke-width="1.5"/>')
    body.append(f'<text x="{left - 8}" y="{base + 32}" font-size="10" text-anchor="end" fill="{BUY}">buys</text>')
    body.append(f'<text x="{left - 8}" y="{base + 42}" font-size="10" text-anchor="end" fill="{SELL}">sells</text>')
    body.append(_legend([(c, n, False) for c, n in zip(LINE_COLORS, names)]
                        + [(SUBTLE, f"${start_cash:,.0f} start", True)], 378))
    return _frame("Value of each bot", "Daily closes. Ticks at the bottom are the rotation bot's "
                  "buys (green) and sells (red).", "".join(body), 395)


def holdings_chart(days, go_live):
    """A row per coin; green where the rotation bot held it."""
    coins = []
    for d in days:
        for c in d["holdings"]:
            if c not in coins:
                coins.append(c)
    dates = [d["date"] for d in days]
    row, top = 20, 64
    left, right = 70, WIDTH - 20
    base = top + row * max(1, len(coins))
    x_of = lambda d: left + (d - dates[0]).days / max(1, (dates[-1] - dates[0]).days) * (right - left)
    day_width = (right - left) / max(1, len(dates))
    body = []
    for i, c in enumerate(coins):
        y = top + i * row
        body.append(f'<text x="{left - 8}" y="{y + 14}" font-size="11" text-anchor="end" fill="{TEXT}">{c}</text>')
        body.append(f'<line x1="{left}" y1="{y + row - 0.5}" x2="{right}" y2="{y + row - 0.5}" stroke="{GRID}"/>')
        start = None
        for k, d in enumerate(days + [None]):
            held = d is not None and c in d["holdings"]
            if held and start is None:
                start = k
            if not held and start is not None:
                x0 = x_of(dates[start])
                x1 = x_of(dates[k - 1]) + day_width
                body.append(f'<rect x="{x0:.1f}" y="{y + 4}" width="{max(1.5, x1 - x0):.1f}" '
                            f'height="{row - 8}" rx="2" fill="{HELD}"/>')
                start = None
    body.append(_x_axis(dates, x_of, base, left, right))
    body.append(_go_live_marker(go_live, dates, x_of, top - 6, base))
    if not coins:
        body.append(f'<text x="{WIDTH / 2}" y="{top + 20}" text-anchor="middle" fill="{SUBTLE}">'
                    'No coins held yet</text>')
    return _frame("What the rotation bot held, and when",
                  "Each green bar is a stretch of days a coin was owned. Gaps are sells; "
                  "no bars at all means the bot was in cash.", "".join(body), base + 30)


def drawdown_chart(series):
    names = list(series)
    dates = [d for d, _ in series[names[0]]]
    left, right, top, base = 70, WIDTH - 20, 70, 250
    falls = {}
    for n in names:
        peak, out = 0.0, []
        for d, v in series[n]:
            peak = max(peak, v)
            out.append((d, (1 - v / peak) * 100))
        falls[n] = out
    worst = max(f for s in falls.values() for _, f in s)
    bottom = max(10, -(-worst // 10) * 10)
    x_of = lambda d: left + (d - dates[0]).days / max(1, (dates[-1] - dates[0]).days) * (right - left)
    y_of = lambda f: top + f / bottom * (base - top)
    body = []
    for f in range(0, int(bottom) + 1, 10):
        y = y_of(f)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{GRID}"/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end" '
                    f'fill="{SUBTLE}">-{f}%</text>')
    body.append(_x_axis(dates, x_of, base, left, right))
    for color, n in zip(LINE_COLORS, names):
        pts = " ".join(f"{x_of(d):.1f},{y_of(f):.1f}" for d, f in falls[n])
        body.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    body.append(_legend([(c, n, False) for c, n in zip(LINE_COLORS, names)], base + 40))
    return _frame("Drop from each bot's high", "0% means at a new high. Lower is a bigger fall.",
                  "".join(body), base + 55)
