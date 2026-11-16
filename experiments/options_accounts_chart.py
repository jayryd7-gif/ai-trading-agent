"""
options_accounts_chart.py - One chart of all three options paper accounts over the past year
(backtest of each account's real rules and stocks): the account lines, the best and worst
days marked on them, and a card per account with its stocks, best days and worst days.

    PYTHONPATH=agents:experiments python3 experiments/options_accounts_chart.py

Writes reports/charts/options-accounts-year.svg (option prices are estimates).
"""

import math
import os
from datetime import timedelta
from xml.sax.saxutils import escape

import yfinance as yf

import wheel_rules as R
from income_strategies import spreads
from wheel_backtest import OURS, RYAN, simulate

OUT = os.path.join("reports", "charts", "options-accounts-year.svg")
W = 1000
# colours: the first three slots of the validated chart palette (distinct for colour-blind viewers too)
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
ACCOUNTS = [
    {"key": "wheel", "name": "Wheel", "sub": "$10K CAD · cheaper stocks", "color": "#2a78d6", "cur": "CAD"},
    {"key": "ryan", "name": "Ryan-style wheel", "sub": "$200K USD (pretend) · his stocks", "color": "#eb6834", "cur": "USD"},
    {"key": "condor", "name": "Iron condors", "sub": "$10K CAD · SPY + QQQ", "color": "#1baf7a", "cur": "CAD"},
]


def money(v, cur):
    v = round(v)
    return f"{'+' if v >= 0 else '−'}${abs(v):,} {cur}"


def run():
    fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
    ryan = R.ACCOUNTS["ryan"]["universe"]
    c = yf.download(sorted(set(R.UNIVERSE + ryan + ["SPY", "QQQ"])), period="3y", progress=False)["Close"].ffill()
    start = c.index[-1] - timedelta(days=365)
    days = [d for d in c.index if d >= start]
    usd10k = R.START_CAD * fx
    out = {}
    _, _, st, _ = simulate(c[R.UNIVERSE].dropna(axis=1, how="all"), usd10k, days, False, False, OURS)
    out["wheel"] = (st["history"], st["tvals"], usd10k, fx)
    _, _, st, _ = simulate(c[ryan], 200_000.0, days, False, False, RYAN)
    out["ryan"] = (st["history"], st["tvals"], 200_000.0, 1.0)
    hist, _, _ = spreads(c, usd10k, days, ["SPY", "QQQ"], dte=30, delta=0.20, width_pct=0.02, tp=0.5,
                         time_exit=14, risk_per_trade=0.15, max_risk=0.36, stop=2.0, calls=True)
    out["condor"] = (hist, spreads.tvals, usd10k, fx)
    return out


def analyse(hist, tvals, start, fx):
    pct = [(d, (e / start - 1) * 100) for d, e in hist]
    days = []
    for i in range(1, len(hist)):
        pnl = (hist[i][1] - hist[i - 1][1]) / fx
        a, b = tvals[i - 1], tvals[i]
        moves = {t: (b.get(t, 0) - a.get(t, 0)) / fx for t in set(a) | set(b)}
        top = max(moves, key=lambda t: moves[t] * (1 if pnl >= 0 else -1)) if moves else "-"
        days.append({"i": i, "date": hist[i][0], "pnl": pnl, "stock": top})
    best = sorted(days, key=lambda x: -x["pnl"])[:3]
    worst = sorted(days, key=lambda x: x["pnl"])[:3]
    traded = sorted({t for tv in tvals for t, v in tv.items() if abs(v) > 0.01})
    return pct, best, worst, traded, (hist[-1][1] - start) / fx


def draw(data):
    a_top, a_h, left, right = 96, 330, 64, W - 150
    parts = []
    allpct = [p for k in data for _, p in data[k]["pct"]]
    lo, hi = min(allpct + [0]), max(allpct + [0])
    step = 5 if hi - lo <= 40 else 10
    lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
    dates = [d for d, _ in data["wheel"]["pct"]]
    n = len(dates)

    def x(i):
        return left + (right - left) * i / (n - 1)

    def y(v):
        return a_top + a_h - (v - lo) / (hi - lo) * a_h

    # grid + y labels
    v = lo
    while v <= hi + 1e-9:
        parts.append(f'<line x1="{left}" x2="{right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID if v else "#c9c8c3"}" '
                     f'stroke-width="1"/>')
        parts.append(f'<text x="{left - 10}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">'
                     f'{"+" if v > 0 else ""}{v:g}%</text>')
        v += step
    # month labels
    seen, last_x = set(), -999
    for i, d in enumerate(dates):
        key = (d.year, d.month)
        if key in seen:
            continue
        seen.add(key)
        nxt = next((j for j in range(i + 1, n) if (dates[j].year, dates[j].month) != key), None)
        if i == 0 and nxt is not None and x(nxt) - x(0) < 60:
            continue                      # first partial month: too short to label
        last_x = x(i)
        if i > 0:
            parts.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{a_top + a_h}" y2="{a_top + a_h + 5}" stroke="{MUTED}"/>')
        label = d.strftime("%b") + (f" ’{d:%y}" if d.month == 1 or i == 0 else "")
        parts.append(f'<text x="{x(i) + 3:.1f}" y="{a_top + a_h + 20}" font-size="11" fill="{INK2}">{label}</text>')
    # lines
    ends = []
    for acc in ACCOUNTS:
        pts = data[acc["key"]]["pct"]
        path = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(p):.1f}" for i, (_, p) in enumerate(pts))
        parts.append(f'<path d="{path}" fill="none" stroke="{acc["color"]}" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append([y(pts[-1][1]), acc, pts[-1][1]])
    # end labels (nudged apart)
    ends.sort(key=lambda e: e[0])
    for k in range(1, len(ends)):
        ends[k][0] = max(ends[k][0], ends[k - 1][0] + 30)
    for yy, acc, p in ends:
        parts.append(f'<circle cx="{right:.1f}" cy="{y(p):.1f}" r="3.5" fill="{acc["color"]}"/>')
        parts.append(f'<text x="{right + 10}" y="{yy:.1f}" font-size="12" font-weight="700" fill="{INK}">'
                     f'{escape(acc["name"].split(" ")[0] if acc["key"] != "condor" else "Condors")}</text>')
        parts.append(f'<text x="{right + 10}" y="{yy + 14:.1f}" font-size="12" fill="{INK2}">'
                     f'{"+" if p >= 0 else "−"}{abs(p):.1f}%</text>')
    # best / worst markers (top 2 of each per account); $ labels where they don't collide
    boxes, labels = [], []

    def free_spot(cx, ty, txt):
        w, h = 6.2 * len(txt), 12
        box = (cx - w / 2, ty - h, cx + w / 2, ty + 2)
        if box[0] < left or box[2] > right + 40:
            return False
        for b in boxes:
            if not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]):
                return False
        boxes.append(box)
        return True

    for acc in ACCOUNTS:
        d = data[acc["key"]]
        for kind, rows in (("best", d["best"][:2]), ("worst", d["worst"][:2])):
            for r in rows:
                cx, cy = x(r["i"]), y(d["pct"][r["i"]][1])
                if kind == "best":
                    tri = f"{cx:.1f},{cy - 13:.1f} {cx - 6:.1f},{cy - 3:.1f} {cx + 6:.1f},{cy - 3:.1f}"
                    ty = cy - 17
                else:
                    tri = f"{cx:.1f},{cy + 13:.1f} {cx - 6:.1f},{cy + 3:.1f} {cx + 6:.1f},{cy + 3:.1f}"
                    ty = cy + 25
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{acc["color"]}" stroke="#fff" stroke-width="1.5"/>')
                parts.append(f'<polygon points="{tri}" fill="{acc["color"]}" stroke="#fff" stroke-width="1"/>')
                lbl = f'{money(r["pnl"], acc["cur"]).replace(" CAD", "").replace(" USD", "")} {r["stock"]}'
                if free_spot(cx, ty, lbl):
                    labels.append(f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="10" font-weight="600" '
                                 f'fill="{INK}" stroke="{SURFACE}" stroke-width="3" paint-order="stroke">{escape(lbl)}</text>')
    parts += labels                       # labels last, so markers never cover them
    # legend for markers
    ly = a_top - 18
    parts.append(f'<polygon points="{left + 6},{ly - 9} {left},{ly + 1} {left + 12},{ly + 1}" fill="{INK2}"/>'
                 f'<text x="{left + 18}" y="{ly}" font-size="11" fill="{INK2}">best days</text>'
                 f'<polygon points="{left + 96},{ly + 3} {left + 90},{ly - 7} {left + 102},{ly - 7}" fill="{INK2}"/>'
                 f'<text x="{left + 108}" y="{ly}" font-size="11" fill="{INK2}">worst days (amount + the stock that moved most)</text>')

    # ---- cards ----
    c_top, c_w, gap = a_top + a_h + 48, (W - 48 - 2 * 16) / 3, 16
    card_h = 330
    for k, acc in enumerate(ACCOUNTS):
        d = data[acc["key"]]
        cx0 = 24 + k * (c_w + gap)
        parts.append(f'<rect x="{cx0:.1f}" y="{c_top}" width="{c_w:.1f}" height="{card_h}" rx="12" fill="#ffffff" '
                     f'stroke="{GRID}"/>')
        parts.append(f'<rect x="{cx0:.1f}" y="{c_top}" width="{c_w:.1f}" height="6" rx="3" fill="{acc["color"]}"/>')
        tx = cx0 + 18
        parts.append(f'<text x="{tx:.1f}" y="{c_top + 32}" font-size="15" font-weight="700" fill="{INK}">{escape(acc["name"])}</text>')
        parts.append(f'<text x="{tx:.1f}" y="{c_top + 50}" font-size="11" fill="{INK2}">{escape(acc["sub"])}</text>')
        total = d["total"]
        parts.append(f'<text x="{tx:.1f}" y="{c_top + 80}" font-size="22" font-weight="700" fill="{INK}">'
                     f'{"+" if d["pct"][-1][1] >= 0 else "−"}{abs(d["pct"][-1][1]):.1f}%</text>')
        parts.append(f'<text x="{tx + 86:.1f}" y="{c_top + 80}" font-size="12" fill="{INK2}">{money(total, acc["cur"])} for the year</text>')
        # stock chips
        chip_x, chip_y = tx, c_top + 98
        for t in d["traded"]:
            wdt = 10 + 7.2 * len(t)
            if chip_x + wdt > cx0 + c_w - 14:
                chip_x, chip_y = tx, chip_y + 24
            parts.append(f'<rect x="{chip_x:.1f}" y="{chip_y}" width="{wdt:.1f}" height="19" rx="9.5" '
                         f'fill="{acc["color"]}" fill-opacity="0.14" stroke="{acc["color"]}" stroke-opacity="0.5"/>')
            parts.append(f'<text x="{chip_x + wdt / 2:.1f}" y="{chip_y + 13.5}" text-anchor="middle" font-size="11" '
                         f'font-weight="600" fill="{INK}">{escape(t)}</text>')
            chip_x += wdt + 6
        yy = max(chip_y + 46, c_top + 160)
        for title, rows, up in (("Best days", d["best"], True), ("Worst days", d["worst"], False)):
            parts.append(f'<text x="{tx:.1f}" y="{yy}" font-size="11" font-weight="700" fill="{INK2}" '
                         f'letter-spacing="0.6">{title.upper()}</text>')
            yy += 18
            for r in rows:
                arrow = "▲" if up else "▼"
                parts.append(f'<text x="{tx:.1f}" y="{yy}" font-size="12" fill="{acc["color"]}">{arrow}</text>'
                             f'<text x="{tx + 16:.1f}" y="{yy}" font-size="12" fill="{INK2}">{r["date"]:%b %d, %Y}</text>'
                             f'<text x="{tx + 128:.1f}" y="{yy}" font-size="12" font-weight="600" fill="{INK}">'
                             f'{money(r["pnl"], acc["cur"])}</text>'
                             f'<text x="{cx0 + c_w - 18:.1f}" y="{yy}" text-anchor="end" font-size="12" fill="{INK2}">'
                             f'{escape(r["stock"])}</text>')
                yy += 18
            yy += 10
        card_h = max(card_h, yy - c_top)
    H = c_top + card_h + 40
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">'
            f'<rect width="{W}" height="{H}" rx="16" fill="{SURFACE}"/>'
            f'<text x="24" y="38" font-size="20" font-weight="700" fill="{INK}">Options paper accounts: the past year</text>'
            f'<text x="24" y="58" font-size="12" fill="{INK2}">% up or down for each account · {dates[0]:%b %d, %Y} '
            f'to {dates[-1]:%b %d, %Y} · backtest of each account\'s own rules and stocks (option prices estimated)</text>')
    foot = (f'<text x="24" y="{H - 16}" font-size="10.5" fill="{MUTED}">Accounts differ in size, so compare by %. '
            f'Dollar amounts are in each account\'s own currency. Not financial advice.</text>')
    return head + "".join(parts) + foot + "</svg>"


def main():
    raw = run()
    data = {}
    for k, (hist, tvals, start, fx) in raw.items():
        pct, best, worst, traded, total = analyse(hist, tvals, start, fx)
        data[k] = {"pct": pct, "best": best, "worst": worst, "traded": traded, "total": total}
        print(k, f"{pct[-1][1]:+.1f}%", "traded:", traded)
        for r in best + worst:
            print(f"   {r['date']:%Y-%m-%d} {r['pnl']:+,.0f} {r['stock']}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(draw(data))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
