"""
condor_trader.py - Paper trades iron condors on SPY and QQQ with a $10K CAD practice
account: a separate monthly cash-flow test, next to the wheel accounts.
Uses REAL option prices from Yahoo Finance.

    PYTHONPATH=agents python agents/condor_trader.py            (normal daily run)
    PYTHONPATH=agents python agents/condor_trader.py --dry-run  (show what it would do, save nothing)

An iron condor = sell a put spread below the price + sell a call spread above it.
It makes money if SPY/QQQ stay between the two short strikes; the most it can lose
is the spread width minus the credit.

Rules (tested in experiments/income_strategies.py; best steady version over 1/3/5 years):
  - SPY and QQQ, one condor each at a time, about 30 days to expiry.
  - Short put and short call at about 0.20 delta, wings about 2% of the price wide.
  - Each condor may risk about 15% of the account (a single contract up to 18%);
    all open condors at most 36%.
  - Close at 50% profit, at 14 days left, or if it costs 2x the credit to close (stop).
  - Paper fills are halfway between the mid price and the worse side, plus $0.65 a leg.

It places NO orders and has no broker access. Every move is sent to your phone (ntfy).
Files in paper-trading/condor/: state.json, trades.csv, journal.md, summary.md, charts.
"""

import csv
import json
import math
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import yfinance as yf

import wheel_charts
import wheel_rules as R
from notify import send

START_CAD = 10_000.0
UNDERLYINGS = ["SPY", "QQQ"]
DTE_MIN, DTE_MAX, DTE_IDEAL = 21, 40, 30
SHORT_DELTA = 0.20
WIDTH_PCT = 0.02
RISK_PER_TRADE, MAX_RISK = 0.15, 0.36
ONE_CONTRACT_MAX = 0.18   # a single condor may risk up to 18% (one $14-wide SPY condor is about 16% of $10K CAD)
TAKE_PROFIT, TIME_EXIT, STOP = 0.50, 14, 2.0
FEE = 0.65

FOLDER = os.path.join("paper-trading", "condor")
STATE = os.path.join(FOLDER, "state.json")
TRADES = os.path.join(FOLDER, "trades.csv")
JOURNAL = os.path.join(FOLDER, "journal.md")
SUMMARY = os.path.join(FOLDER, "summary.md")
NY = ZoneInfo("America/New_York")
DRY = "--dry-run" in sys.argv
events = []


def today_ny():
    return datetime.now(NY).date()


def fill_sell(bid, ask):
    return (bid + (bid + ask) / 2) / 2


def fill_buy(bid, ask):
    return (ask + (bid + ask) / 2) / 2


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
    usd = round(START_CAD * fx, 2)
    return {"started": today_ny().isoformat(), "fx": fx, "start_usd": usd, "cash": usd,
            "positions": {}, "wins": 0, "losses": 0, "history": [], "months": {}}


def describe(p):
    lp, sp, sc, lc = p["long_put"], p["short_put"], p["short_call"], p["long_call"]
    return f"{p['n']}x {lp:g}/{sp:g} puts + {sc:g}/{lc:g} calls exp {p['exp']}"


def record(state, ticker, action, p, price, pnl=None, note=""):
    now = datetime.now(NY).strftime("%Y-%m-%d %H:%M")
    row = {"time_ny": now, "ticker": ticker, "action": action, "condor": describe(p), "contracts": p["n"],
           "price": round(price, 2), "pnl_usd": "" if pnl is None else round(pnl, 2),
           "cash_usd": round(state["cash"], 2), "note": note}
    pnl_txt = "" if pnl is None else f", P/L ${pnl:+.0f} USD ({pnl / state['fx']:+.0f} CAD)"
    line = f"{action} {ticker} iron condor {describe(p)} at ${price:.2f}{pnl_txt}. {note}".strip()
    events.append((f"Condor: {action} {ticker}", line, "high" if "STOP" in note.upper() else "default"))
    print(f"{now}  {line}")
    if DRY:
        return
    if pnl is not None:
        month = now[:7]
        state["months"][month] = round(state["months"].get(month, 0.0) + pnl / state["fx"], 2)
    new = not os.path.exists(TRADES)
    with open(TRADES, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    if not os.path.exists(JOURNAL):
        open(JOURNAL, "w").write("# Iron condor paper account ($10K CAD): journal\n\n")
    with open(JOURNAL, "a") as f:
        f.write(f"- **{now} NY** {line}\n")


def pick_expiry(tk, today):
    best = None
    for e in tk.options:
        dte = (date.fromisoformat(e) - today).days
        if DTE_MIN <= dte <= DTE_MAX and (best is None or abs(dte - DTE_IDEAL) < abs(best[1] - DTE_IDEAL)):
            best = (e, dte)
    return best


def quotes(tk, exp):
    ch = tk.option_chain(exp)
    q = {}
    for kind, table in (("put", ch.puts), ("call", ch.calls)):
        for _, r in table.iterrows():
            q[(kind, float(r["strike"]))] = (float(r["bid"]), float(r["ask"]), float(r["impliedVolatility"] or 0))
    return q


def close_cost(p, q):
    """(what it costs to close now with our fill rule, the mid-price value) or None."""
    legs = [("put", p["short_put"], "buy"), ("put", p["long_put"], "sell"),
            ("call", p["short_call"], "buy"), ("call", p["long_call"], "sell")]
    cost = mid = 0.0
    for kind, K, side in legs:
        if (kind, K) not in q:
            return None
        bid, ask, _ = q[(kind, K)]
        if ask <= 0:
            return None
        cost += fill_buy(bid, ask) if side == "buy" else -fill_sell(bid, ask)
        mid += ((bid + ask) / 2) * (1 if side == "buy" else -1)
    return max(cost, 0.0), max(mid, 0.0)


def settle_value(p, S):
    put = max(0.0, min(p["short_put"] - S, p["short_put"] - p["long_put"]))
    call = max(0.0, min(S - p["short_call"], p["long_call"] - p["short_call"]))
    return put + call


def manage(state, closes, today):
    for t in list(state["positions"]):
        p = state["positions"][t]
        exp = date.fromisoformat(p["exp"])
        if today > exp:
            hist = closes[t].dropna()
            S = float(hist[hist.index.date <= exp].iloc[-1])
            val = settle_value(p, S)
            state["cash"] -= val * 100 * p["n"]
            pnl = (p["credit"] - val) * 100 * p["n"] - 4 * FEE * p["n"]
            state["wins" if pnl >= 0 else "losses"] += 1
            del state["positions"][t]
            record(state, t, "EXPIRED", p, val, pnl, f"{t} closed ${S:.2f} at expiry.")
            continue
        try:
            q = quotes(yf.Ticker(t), p["exp"])
        except Exception as error:
            print(f"{t}: no quotes ({error})")
            continue
        cc = close_cost(p, q)
        if not cc:
            continue
        cost, mid = cc
        p["mark"] = mid
        dte = (exp - today).days
        reason = None
        if cost <= p["credit"] * (1 - TAKE_PROFIT):
            reason = "Hit 50% profit."
        elif mid >= p["credit"] * STOP:
            reason = "Stop: it would cost 2x the credit to close."
        elif dte <= TIME_EXIT:
            reason = f"{dte} days left: closing before the last weeks' big swings."
        if reason:
            state["cash"] -= cost * 100 * p["n"] + 4 * FEE * p["n"]
            pnl = (p["credit"] - cost) * 100 * p["n"] - 8 * FEE * p["n"]
            state["wins" if pnl >= 0 else "losses"] += 1
            del state["positions"][t]
            record(state, t, "CLOSED", p, cost, pnl, reason)


def equity(state):
    return state["cash"] - sum(p.get("mark", p["credit"]) * 100 * p["n"] for p in state["positions"].values())


def open_new(state, closes, today):
    eq = equity(state)
    risk_now = sum(p["risk"] for p in state["positions"].values())
    for t in UNDERLYINGS:
        if t in state["positions"]:
            continue
        tk = yf.Ticker(t)
        S = float(closes[t].dropna().iloc[-1])
        e = pick_expiry(tk, today)
        if not e:
            continue
        exp, dte = e
        try:
            q = quotes(tk, exp)
        except Exception as error:
            print(f"{t}: no quotes ({error})")
            continue
        width = max(1.0, round(S * WIDTH_PCT))

        def short_strike(kind):
            best = None
            for (k, K), (bid, ask, iv) in q.items():
                if k != kind or bid <= 0 or iv < 0.03 or (kind == "put" and K >= S) or (kind == "call" and K <= S):
                    continue
                d = abs(R.bs_delta(S, K, dte / 365, iv, kind))
                if best is None or abs(d - SHORT_DELTA) < best[1]:
                    best = (K, abs(d - SHORT_DELTA), d)
            return best

        sp, sc = short_strike("put"), short_strike("call")
        if not sp or not sc:
            continue
        # wings: the listed strikes closest to one width away
        puts = [K for (k, K), v in q.items() if k == "put" and K < sp[0] and v[1] > 0]
        calls = [K for (k, K), v in q.items() if k == "call" and K > sc[0] and v[1] > 0]
        if not puts or not calls:
            continue
        lp = min(puts, key=lambda K: abs(K - (sp[0] - width)))
        lc = min(calls, key=lambda K: abs(K - (sc[0] + width)))
        width = max(sp[0] - lp, lc - sc[0])
        credit = (fill_sell(*q[("put", sp[0])][:2]) - fill_buy(*q[("put", lp)][:2])
                  + fill_sell(*q[("call", sc[0])][:2]) - fill_buy(*q[("call", lc)][:2]))
        if credit <= 0.05:
            continue
        risk1 = (width - credit) * 100 + 4 * FEE
        n = int(min(RISK_PER_TRADE * eq, MAX_RISK * eq - risk_now) // risk1)
        if n < 1 and risk1 <= ONE_CONTRACT_MAX * eq and risk_now + risk1 <= MAX_RISK * eq:
            n = 1
        if n < 1:
            print(f"{t}: one condor risks ${risk1:,.0f}, more than the limit; skipped")
            continue
        state["cash"] += credit * 100 * n - 4 * FEE * n
        p = {"exp": exp, "short_put": sp[0], "long_put": lp, "short_call": sc[0], "long_call": lc,
             "credit": credit, "n": n, "risk": risk1 * n, "opened": today.isoformat(), "S_open": S}
        state["positions"][t] = p
        risk_now += risk1 * n
        record(state, t, "OPENED", p, credit,
               note=f"{dte} days. {t} at ${S:.2f}. Profit zone ${sp[0]:g}-${sc[0]:g} "
                    f"(short deltas {sp[2]:.2f} / {sc[2]:.2f}). Max gain ${credit * 100 * n:,.0f}, "
                    f"max loss ${risk1 * n:,.0f}.")


def write_summary(state, closes, today):
    eq = equity(state)
    pnl = eq - state["start_usd"]
    fx = state["fx"]
    hist = [h for h in state.get("history", []) if h["date"] != today.isoformat()]
    hist.append({"date": today.isoformat(), "equity_usd": round(eq, 2), "start_usd": state["start_usd"]})
    state["history"] = hist
    rows = []
    for t, p in sorted(state["positions"].items()):
        mark = p.get("mark", p["credit"])
        val = ((p["credit"] - mark) * 100 - 4 * FEE) * p["n"]
        rows.append({"label": f"{t} condor {p['short_put']:g}/{p['short_call']:g} (opened {p['opened'][5:]})",
                     "pnl_cad": val / fx, "pct": val / p["risk"] * 100, "t": t, "p": p, "mark": mark})
    if not DRY:
        wheel_charts.save(FOLDER, hist, fx, rows)
    month = today.strftime("%Y-%m")
    lines = ["# Iron condor paper account ($10K CAD)", "",
             f"Updated {datetime.now(NY):%Y-%m-%d %H:%M} New York. Started {state['started']}. "
             "Goal: steady monthly cash flow from SPY/QQQ iron condors.", "",
             "| | |", "|---|---|",
             f"| Account value | **${eq / fx:,.0f} CAD** (${eq:,.0f} USD) |",
             f"| Up / down | **{pnl / fx:+,.0f} CAD** ({round(pnl / state['start_usd'] * 100, 1) + 0.0:+.1f}%) |",
             f"| Closed this month ({month}) | **{state['months'].get(month, 0):+,.0f} CAD** |",
             f"| Closed trades | {state['wins']} wins, {state['losses']} losses |",
             f"| Money at risk now | ${sum(p['risk'] for p in state['positions'].values()) / fx:,.0f} CAD "
             f"(limit 36% of the account) |", "",
             "![Account profit / loss](value.svg)", "",
             "## Open condors", "", "![Open condors](holdings.svg)", "",
             "| Underlying | Condor | Opened | Price then / now | Credit | Worth now | Up / down CAD | Max loss CAD |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        p, t = r["p"], r["t"]
        S = float(closes[t].dropna().iloc[-1])
        lines.append(f"| {t} | {describe(p)} | {p['opened']} | ${p['S_open']:.2f} / ${S:.2f} | ${p['credit']:.2f} "
                     f"| ${r['mark']:.2f} | {'🟢' if r['pnl_cad'] >= 0 else '🔴'} {r['pnl_cad']:+,.0f} "
                     f"| {p['risk'] / fx:,.0f} |")
    if not rows:
        lines.append("| (none open) | | | | | | | |")
    lines += ["", "## Cash flow by month (closed trades, CAD)", "", "| Month | Profit / loss |", "|---|---|"]
    for m, v in sorted(state["months"].items()):
        lines.append(f"| {m} | {'🟢' if v >= 0 else '🔴'} {v:+,.0f} |")
    if not state["months"]:
        lines.append("| (no closed trades yet) | |")
    lines += ["", "Prices from Yahoo Finance option chains. Paper only: no real orders. "
              "Rules: agents/condor_trader.py. Every move: [journal.md](journal.md)."]
    if not DRY:
        open(SUMMARY, "w").write("\n".join(lines) + "\n")
    return eq


def main():
    today = today_ny()
    if today.weekday() >= 5 and not DRY and "--force" not in sys.argv:
        print("Weekend, nothing to do.")
        return
    os.makedirs(FOLDER, exist_ok=True)
    state = load_state()
    closes = yf.download(UNDERLYINGS, period="3mo", progress=False)["Close"]
    manage(state, closes, today)
    open_new(state, closes, today)
    eq = write_summary(state, closes, today)
    print(f"\nIron condor account: ${eq / state['fx']:,.0f} CAD, {len(state['positions'])} open.")
    if DRY:
        print("(dry run: nothing saved, no phone alerts)")
        return
    json.dump(state, open(STATE, "w"), indent=1)
    for title, msg, prio in events:
        send(title, msg, priority=prio, tags="moneybag")


if __name__ == "__main__":
    main()
