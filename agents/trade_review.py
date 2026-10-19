"""
trade_review.py - What could have gone better, and a chart, for each paper trade.

Plain code, no AI, so it costs nothing. paper_trader.py calls it once per
closed trade.

  review(result, session)   -> facts and lessons for the journal
  draw(result, candles, ...)-> an SVG chart of the trade, saved in paper-trading/charts
  tradingview_link(...)     -> the matching TradingView chart
"""

import os
from datetime import timedelta
from xml.sax.saxutils import escape

from risk import INSTRUMENTS

CHART_FOLDER = os.path.join("paper-trading", "charts")
TV_SYMBOLS = {"nasdaq": "CME_MINI:MNQ1!", "gold": "COMEX_MINI:MGC1!"}

UP, DOWN, TEXT, SUBTLE, GRID = "#2da44e", "#cf222e", "#1f2328", "#656d76", "#d0d7de"
LEVEL, ENTRY, TARGET, STOP = "#8250df", "#0969da", "#2da44e", "#cf222e"


def money(value):
    return f"-${-value:,.0f}" if value < 0 else f"${value:,.0f}"


def tradingview_link(instrument):
    symbol = TV_SYMBOLS[instrument].replace(":", "%3A").replace("!", "%21")
    return f"https://www.tradingview.com/chart/?symbol={symbol}&interval=5"


def review(result, session):
    """Facts about the trade and a list of plain-English lessons.

    session: [(time, candle), ...] for the whole session the trade was in.
    """
    d = 1 if result["direction"] == "long" else -1
    entry, stop = result["entry"], result["stop"]
    spec = INSTRUMENTS[result["instrument"]]
    spacing, pv = spec["target_spacing"], spec["point_value"]
    plan = result["sell_plan"]
    fills = result["fills"]
    after = session[result["entry_index"] + 1:]
    inside = [(t, c) for t, c in after if t <= result["exit_time"]]
    later = [(t, c) for t, c in after if t > result["exit_time"]]

    def best(c):    # points in the trade's favour at this candle's best price
        return d * ((c.high if d == 1 else c.low) - entry)

    def worst(c):   # points against the trade at this candle's worst price
        return d * (entry - (c.low if d == 1 else c.high))

    mfe = max((best(c) for _, c in inside), default=0.0)
    mae = max((worst(c) for _, c in inside), default=0.0)
    after_best = max(((best(c), t) for t, c in later), default=(None, None))
    level = result["key_high"] if d == 1 else result["key_low"]
    chase = d * (entry - level)
    risk_pts = abs(entry - stop)
    targets_hit = sum(1 for f in fills if f["what"].startswith("Target"))
    stopped = any(f["what"] == "Stop" for f in fills)
    ended = any(f["what"] == "Session end" for f in fills)
    net = result["profit"]

    lessons = []
    if net <= 0:
        if targets_hit == 0:
            lessons.append(f"Price never reached Target 1: the best it did was "
                           f"{mfe:+.2f} points, and Target 1 needed {spacing}.")
            if stopped and after_best[0] is not None and after_best[0] >= spacing:
                lessons.append(
                    f"After the stop, price turned and reached {after_best[0]:+.2f} points "
                    f"by {after_best[1]:%H:%M}. The stop ({risk_pts:.2f} points from entry) "
                    f"was too tight: a stop just past the key level ({level}) would have "
                    "kept you in.")
            elif stopped:
                lessons.append("The breakout failed and price kept going the other way, "
                               "so the stop did its job and kept the loss small.")
        else:
            t1 = sum(f["profit"] for f in fills if f["what"].startswith("Target"))
            lessons.append(f"Target 1 paid {money(t1)}, but the stop stayed at the start. "
                           f"Moving it to breakeven after Target 1 would have ended this "
                           f"trade at about {money(t1)} instead of {money(net)}.")
        if chase > spacing / 2:
            lessons.append(f"The entry was {chase:.2f} points past the key level, chasing a "
                           "stretched move. Waiting for a pullback toward the level would "
                           "have meant a better price and a smaller risk.")
        if ended:
            lessons.append("It was still open at the session end and closed at a loss. "
                           "A time limit (out by 2 hours with no Target 1) would have "
                           "freed the money earlier.")
    else:
        if targets_hit == len(plan):
            extra_pts = (after_best[0] or 0) - len(plan) * spacing
            if extra_pts > spacing / 2:
                extra = extra_pts * pv * plan[-1]
                lessons.append(
                    f"Price kept going {extra_pts:.2f} points past Target 3 (by "
                    f"{after_best[1]:%H:%M}). Letting the last {plan[-1]} contract(s) run "
                    f"with a trailing stop could have made up to {money(extra)} more.")
            else:
                lessons.append("Clean trade: price stalled near Target 3, so taking the "
                               "full profit there was right.")
        elif stopped:
            reached = (after_best[0] or 0) >= len(plan) * spacing
            if reached:
                lessons.append(
                    f"The last contracts were stopped at Target 1, then price reached "
                    f"Target 3 by {after_best[1]:%H:%M}. A looser stop after Target 2 "
                    "would have caught it.")
            else:
                lessons.append("Moving the stop to Target 1 after Target 2 locked in the "
                               "profit; price never reached Target 3 afterwards.")
        if ended:
            lessons.append("Part of the trade was closed at the session end, before "
                           "Target 3. A smaller final target would have paid sooner.")
    lessons.append(f"Biggest move against you while in the trade: {mae:.2f} points "
                   f"({money(mae * pv * result['contracts'])} on paper). Best move for you: "
                   f"{mfe:.2f} points.")
    return {"mfe": round(mfe, 2), "mae": round(mae, 2), "lessons": lessons}


def draw(result, candles, path):
    """SVG candle chart from 2 hours before the open to an hour after the exit,
    with the key levels, entry, stop, targets and every fill marked."""
    start = result["session_start"]
    shown = [(t, c) for t, c in candles
             if start - timedelta(hours=2) <= t <= result["exit_time"] + timedelta(hours=1)]
    if not shown:
        return None
    spec = INSTRUMENTS[result["instrument"]]
    d = 1 if result["direction"] == "long" else -1
    targets = [round(result["entry"] + d * spec["target_spacing"] * n, 2)
               for n in range(1, len(result["sell_plan"]) + 1)]
    lines = [(result["key_high"], LEVEL, "key high"), (result["key_low"], LEVEL, "key low"),
             (result["entry"], ENTRY, "entry"), (result["stop"], STOP, "stop")]
    lines += [(p, TARGET, f"T{n}") for n, p in enumerate(targets, 1)]
    prices = [c.high for _, c in shown] + [c.low for _, c in shown] + [p for p, _, _ in lines]
    top, bottom = max(prices), min(prices)
    pad = (top - bottom) * 0.05 or 1
    top, bottom = top + pad, bottom - pad

    width, height, left, right, upper, lower = 900, 420, 60, 70, 60, 40
    plot_w, plot_h = width - left - right, height - upper - lower
    step = plot_w / len(shown)

    def y(price):
        return upper + (top - price) / (top - bottom) * plot_h

    def x(i):
        return left + step * (i + 0.5)

    body = []
    for price, color, label in lines:
        body.append(f'<line x1="{left}" x2="{width - right}" y1="{y(price):.1f}" '
                    f'y2="{y(price):.1f}" stroke="{color}" stroke-dasharray="4 3"/>')
        body.append(f'<text x="{width - right + 4}" y="{y(price) + 4:.1f}" font-size="11" '
                    f'fill="{color}">{escape(label)} {price}</text>')
    open_x = None
    for i, (t, c) in enumerate(shown):
        o = c.open if c.open is not None else (shown[i - 1][1].close if i else c.close)
        color = UP if c.close >= o else DOWN
        body.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(c.high):.1f}" '
                    f'y2="{y(c.low):.1f}" stroke="{color}"/>')
        h = max(abs(y(o) - y(c.close)), 1)
        body.append(f'<rect x="{x(i) - step * 0.35:.1f}" y="{min(y(o), y(c.close)):.1f}" '
                    f'width="{step * 0.7:.1f}" height="{h:.1f}" fill="{color}"/>')
        if t == start:
            open_x = x(i) - step / 2
        if i % 12 == 0:
            body.append(f'<text x="{x(i):.1f}" y="{height - lower + 16}" font-size="10" '
                        f'text-anchor="middle" fill="{SUBTLE}">{t:%H:%M}</text>')
    if open_x:
        body.append(f'<line x1="{open_x:.1f}" x2="{open_x:.1f}" y1="{upper}" '
                    f'y2="{height - lower}" stroke="{SUBTLE}"/>')
        body.append(f'<text x="{open_x + 3:.1f}" y="{upper + 12}" font-size="10" '
                    f'fill="{SUBTLE}">open</text>')
    index = {t.strftime("%H:%M"): i for i, (t, _) in enumerate(shown)}
    marks = [(f"{result['entry_time']:%H:%M}", result["entry"], ENTRY,
              f"{'BUY' if d == 1 else 'SELL'} {result['contracts']}")]
    marks += [(f["time"], f["price"], STOP if f["profit"] < 0 else TARGET,
               f"{'sell' if d == 1 else 'cover'} {f['contracts']}") for f in result["fills"]]
    for n, (when, price, color, label) in enumerate(marks):
        if when not in index:
            continue
        cx, cy = x(index[when]), y(price)
        body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{color}" '
                    f'stroke="#fff"/>')
        dy = -10 - (n % 2) * 12
        body.append(f'<text x="{cx:.1f}" y="{cy + dy:.1f}" font-size="11" font-weight="bold" '
                    f'text-anchor="middle" fill="{color}">{escape(label)}</text>')

    name = {"nasdaq": "Nasdaq (MNQ)", "gold": "Gold (MGC)"}[result["instrument"]]
    title = (f"{name} {result['direction']} {result['date']}: "
             f"{money(result['profit'])} before fees")
    sub = "5-minute candles, New York time. Dashed lines: key levels, entry, stop, targets."
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">'
           f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
           f'fill="#ffffff" stroke="{GRID}"/>'
           f'<text x="20" y="28" font-size="16" font-weight="bold" fill="{TEXT}">'
           f'{escape(title)}</text>'
           f'<text x="20" y="46" font-size="12" fill="{SUBTLE}">{escape(sub)}</text>'
           + "".join(body) + "</svg>")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(svg)
    return path
