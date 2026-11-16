"""
overview_chart.py - Draws the "overview" chart style used on the dashboard (SVG, no extra tools):

  - top: one line per account over time, with the best (▲) and worst (▼) days or trades
    marked and labelled
  - bottom: one card per account with its headline result, tags (stocks, contract
    counts...) and short lists (best trades, worst trades, best times...)

Used by experiments/options_accounts_chart.py (backtest), agents/options_live_chart.py
(the live options accounts) and agents/futures_chart.py (Nasdaq + gold paper trades).

An account is a dict:
  name, sub, color            card title, small line under it, line / accent colour
  series                      [(date, value), ...] for the line (value in `unit`)
  markers                     [(date, value_on_line, "best"|"worst", label), ...]
  headline, headline_sub      big number on the card + text beside it
  chips                       short tags shown as pills
  sections                    [(title, [(arrow, col1, col2, col3), ...]), ...]
"""

import math
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

W = 1000
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
# the first three slots of the validated chart palette: distinct for colour-blind viewers too
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
NEUTRAL = "#8a8984"


def _day(d):
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def _fmt(v, unit):
    if unit == "%":
        v = round(v, 1) + 0.0
        return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v):g}%"
    v = round(v)
    return f"{'+' if v > 0 else '−' if v < 0 else ''}${abs(v):,}"


def draw(title, subtitle, accounts, unit="%", footnote="", empty="Starts with the first trade"):
    a_top, a_h, left, right = 96, 300, 70, W - 150
    parts, labels, boxes = [], [], []
    days = sorted({_day(d) for a in accounts for d, _ in a["series"]})
    has_data = len(days) >= 2
    vals = [v for a in accounts for _, v in a["series"]] + [0]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1e-9)
    raw = span / 6
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    if unit == "%":
        step = max(step, 1)
    lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
    if hi == lo:
        hi = lo + step
    d0, d1 = (days[0], days[-1]) if days else (date.today(), date.today() + timedelta(days=1))
    total_days = max((d1 - d0).days, 1)

    def x(d):
        return left + (right - left) * (_day(d) - d0).days / total_days

    def y(v):
        return a_top + a_h - (v - lo) / (hi - lo) * a_h

    v = lo
    while v <= hi + 1e-9:
        parts.append(f'<line x1="{left}" x2="{right}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
                     f'stroke="{GRID if abs(v) > 1e-9 else "#c9c8c3"}" stroke-width="1"/>')
        parts.append(f'<text x="{left - 10}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" '
                     f'fill="{MUTED}">{_fmt(v, unit)}</text>')
        v += step
    if not has_data:
        parts.append(f'<text x="{(left + right) / 2}" y="{a_top + a_h / 2}" text-anchor="middle" font-size="15" '
                     f'fill="{INK2}">{escape(empty)}</text>')
    else:
        # time labels: months for long spans, days for short ones
        if total_days > 75:
            d = date(d0.year, d0.month, 1)
            while d <= d1:
                if d > d0 and x(d) - left > 30:
                    parts.append(f'<line x1="{x(d):.1f}" x2="{x(d):.1f}" y1="{a_top + a_h}" y2="{a_top + a_h + 5}" stroke="{MUTED}"/>')
                    lab = d.strftime("%b") + (f" ’{d:%y}" if d.month == 1 else "")
                    parts.append(f'<text x="{x(d) + 3:.1f}" y="{a_top + a_h + 20}" font-size="11" fill="{INK2}">{lab}</text>')
                d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        else:
            every = max(1, round(total_days / 8))
            d = d0
            while d <= d1:
                parts.append(f'<text x="{x(d):.1f}" y="{a_top + a_h + 20}" text-anchor="middle" font-size="11" '
                             f'fill="{INK2}">{d:%b} {d.day}</text>')
                d += timedelta(days=every)
    ends = []
    for a in accounts:
        pts = sorted(((_day(d), v) for d, v in a["series"]), key=lambda p: p[0])
        if not pts:
            continue
        if len(pts) > 1:
            path = " ".join(f"{'M' if i == 0 else 'L'}{x(d):.1f},{y(v):.1f}" for i, (d, v) in enumerate(pts))
            parts.append(f'<path d="{path}" fill="none" stroke="{a["color"]}" stroke-width="2" '
                         f'stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append([y(pts[-1][1]), a, pts[-1]])
    if has_data:
        ends.sort(key=lambda e: e[0])
        for k in range(1, len(ends)):
            ends[k][0] = max(ends[k][0], ends[k - 1][0] + 30)
        for yy, a, (d, v) in ends:
            parts.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="3.5" fill="{a["color"]}"/>')
            parts.append(f'<text x="{right + 10}" y="{yy:.1f}" font-size="12" font-weight="700" fill="{INK}">'
                         f'{escape(a.get("short", a["name"]))}</text>')
            parts.append(f'<text x="{right + 10}" y="{yy + 14:.1f}" font-size="12" fill="{INK2}">{_fmt(v, unit)}</text>')

    def free_spot(cx, ty, txt):
        w = 6.2 * len(txt)
        box = (cx - w / 2, ty - 12, cx + w / 2, ty + 2)
        if box[0] < left - 10 or box[2] > right + 30:
            return False
        if any(not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]) for b in boxes):
            return False
        boxes.append(box)
        return True

    if has_data:
        for a in accounts:
            for d, v, kind, lbl in a.get("markers", []):
                cx, cy = x(d), y(v)
                if kind == "best":
                    tri, ty = f"{cx:.1f},{cy - 13:.1f} {cx - 6:.1f},{cy - 3:.1f} {cx + 6:.1f},{cy - 3:.1f}", cy - 17
                else:
                    tri, ty = f"{cx:.1f},{cy + 13:.1f} {cx - 6:.1f},{cy + 3:.1f} {cx + 6:.1f},{cy + 3:.1f}", cy + 25
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{a["color"]}" stroke="#fff" stroke-width="1.5"/>')
                parts.append(f'<polygon points="{tri}" fill="{a["color"]}" stroke="#fff" stroke-width="1"/>')
                if free_spot(cx, ty, lbl):
                    labels.append(f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="10" font-weight="600" '
                                  f'fill="{INK}" stroke="{SURFACE}" stroke-width="3" paint-order="stroke">{escape(lbl)}</text>')
    parts += labels
    ly = a_top - 18
    parts.append(f'<polygon points="{left + 6},{ly - 9} {left},{ly + 1} {left + 12},{ly + 1}" fill="{INK2}"/>'
                 f'<text x="{left + 18}" y="{ly}" font-size="11" fill="{INK2}">best</text>'
                 f'<polygon points="{left + 60},{ly + 3} {left + 54},{ly - 7} {left + 66},{ly - 7}" fill="{INK2}"/>'
                 f'<text x="{left + 72}" y="{ly}" font-size="11" fill="{INK2}">worst</text>')

    # ---- cards (one row of up to 3; more than 3 go in rows of 2) ----
    n = len(accounts)
    cols = n if n <= 3 else 2
    gap = 16
    c_w = (W - 48 - (cols - 1) * gap) / cols

    def card(a, cx0, top):
        tx = cx0 + 18
        body = []
        body.append(f'<text x="{tx:.1f}" y="{top + 32}" font-size="15" font-weight="700" fill="{INK}">{escape(a["name"])}</text>')
        body.append(f'<text x="{tx:.1f}" y="{top + 50}" font-size="11" fill="{INK2}">{escape(a.get("sub", ""))}</text>')
        body.append(f'<text x="{tx:.1f}" y="{top + 80}" font-size="22" font-weight="700" fill="{INK}">'
                    f'{escape(a.get("headline", ""))}</text>')
        hw = 14 * len(a.get("headline", "")) + 8
        body.append(f'<text x="{tx + hw:.1f}" y="{top + 80}" font-size="12" fill="{INK2}">{escape(a.get("headline_sub", ""))}</text>')
        chip_x, chip_y = tx, top + 98
        for t in a.get("chips", []):
            wdt = 10 + 6.6 * len(t)
            if chip_x + wdt > cx0 + c_w - 14:
                chip_x, chip_y = tx, chip_y + 24
            body.append(f'<rect x="{chip_x:.1f}" y="{chip_y}" width="{wdt:.1f}" height="19" rx="9.5" '
                        f'fill="{a["color"]}" fill-opacity="0.14" stroke="{a["color"]}" stroke-opacity="0.5"/>')
            body.append(f'<text x="{chip_x + wdt / 2:.1f}" y="{chip_y + 13.5}" text-anchor="middle" font-size="11" '
                        f'font-weight="600" fill="{INK}">{escape(t)}</text>')
            chip_x += wdt + 6
        yy = (chip_y + 46) if a.get("chips") else top + 112
        for title_s, rows in a.get("sections", []):
            body.append(f'<text x="{tx:.1f}" y="{yy}" font-size="11" font-weight="700" fill="{INK2}" '
                        f'letter-spacing="0.6">{escape(title_s.upper())}</text>')
            yy += 18
            if not rows:
                body.append(f'<text x="{tx:.1f}" y="{yy}" font-size="12" fill="{MUTED}">none yet</text>')
                yy += 18
            for arrow, c1, c2, c3 in rows:
                if a.get("two_line"):
                    body.append(f'<text x="{tx:.1f}" y="{yy}" font-size="12" fill="{a["color"]}">{escape(arrow)}</text>'
                                f'<text x="{tx + 16:.1f}" y="{yy}" font-size="12" fill="{INK2}">{escape(c1)}</text>'
                                f'<text x="{tx + min(0.26 * c_w, 80):.1f}" y="{yy}" font-size="12" font-weight="600" fill="{INK}">{escape(c2)}</text>'
                                f'<text x="{tx + 16:.1f}" y="{yy + 15}" font-size="11" fill="{MUTED}">{escape(c3)}</text>')
                    yy += 36
                    continue
                body.append(f'<text x="{tx:.1f}" y="{yy}" font-size="12" fill="{a["color"]}">{escape(arrow)}</text>'
                            f'<text x="{tx + 16:.1f}" y="{yy}" font-size="12" fill="{INK2}">{escape(c1)}</text>'
                            f'<text x="{tx + min(0.36 * c_w, 150):.1f}" y="{yy}" font-size="12" font-weight="600" fill="{INK}">{escape(c2)}</text>'
                            f'<text x="{cx0 + c_w - 18:.1f}" y="{yy}" text-anchor="end" font-size="11" fill="{INK2}">{escape(c3)}</text>')
                yy += 18
            yy += 10
        return body, yy - top + 6

    top = a_top + a_h + 48
    for r0 in range(0, n, cols):
        row = accounts[r0:r0 + cols]
        made = [card(a, 24 + k * (c_w + gap), top) + (24 + k * (c_w + gap), a) for k, a in enumerate(row)]
        h = max(m[1] for m in made)
        for body, _, cx0, a in made:
            parts.append(f'<rect x="{cx0:.1f}" y="{top}" width="{c_w:.1f}" height="{h}" rx="12" fill="#ffffff" stroke="{GRID}"/>')
            parts.append(f'<rect x="{cx0:.1f}" y="{top}" width="{c_w:.1f}" height="6" rx="3" fill="{a["color"]}"/>')
            parts += body
        top += h + gap
    c_top, card_h = top - gap, 0
    H = c_top + card_h + 40
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">'
            f'<rect width="{W}" height="{H}" rx="16" fill="{SURFACE}"/>'
            f'<text x="24" y="38" font-size="20" font-weight="700" fill="{INK}">{escape(title)}</text>'
            f'<text x="24" y="58" font-size="12" fill="{INK2}">{escape(subtitle)}</text>')
    foot = f'<text x="24" y="{H - 16}" font-size="10.5" fill="{MUTED}">{escape(footnote)}</text>'
    return head + "".join(parts) + foot + "</svg>"
