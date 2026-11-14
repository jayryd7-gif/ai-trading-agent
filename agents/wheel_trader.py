"""
wheel_trader.py - Paper trades the options wheel on practice accounts (ours: $10K CAD;
"ryan": Options With Ryan's rules, pretend $200K USD on his stocks),
using REAL option prices from Yahoo Finance (bid/ask, open interest, implied vol).

    PYTHONPATH=agents python agents/wheel_trader.py            (normal daily run)
    PYTHONPATH=agents python agents/wheel_trader.py --dry-run  (show what it would do, save nothing)
    PYTHONPATH=agents python agents/wheel_trader.py --account ryan   (the Ryan-style account)

Runs once each weekday on GitHub during market hours (.github/workflows/wheel-paper.yml).
Every move (sell, buy back, assignment, called away) is sent to your phone (ntfy).

Rules (agents/wheel_rules.py, research in experiments/wheel-strategy-research.md):
  - Up to 4 stocks at once; one stock may tie up at most 25% of the account.
  - Sell a ~0.30 delta cash-secured put, 30-50 days out. No earnings before expiry.
  - Buy it back at 50% profit. At 21 days left: close if out of the money,
    otherwise hold to expiry and take the 100 shares.
  - Own shares -> sell a ~0.30 delta covered call at or above the cost basis.
    Called away -> the slot is free for a new put.
  - Paper fills are halfway between the mid price and the bid (selling) or ask
    (buying), plus $0.65 per contract, so results are not flattered.

It places NO orders and has no broker access.

Files in paper-trading/wheel/:
  state.json   cash, positions, open options (the bot's memory)
  trades.csv   every move
  journal.md   every move in plain words
  summary.md   account value, P/L in CAD, open positions
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

ACCOUNT = sys.argv[sys.argv.index("--account") + 1] if "--account" in sys.argv else "ours"
A = R.ACCOUNTS[ACCOUNT]
FOLDER = A["folder"]
STATE = os.path.join(FOLDER, "state.json")
TRADES = os.path.join(FOLDER, "trades.csv")
JOURNAL = os.path.join(FOLDER, "journal.md")
SUMMARY = os.path.join(FOLDER, "summary.md")
NY = ZoneInfo("America/New_York")
DRY = "--dry-run" in sys.argv

events = []          # (title, message, priority) sent to the phone at the end


# ---------------- helpers ----------------

def today_ny():
    return datetime.now(NY).date()


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    if A["start_usd"]:                     # a USD account: show everything in USD
        fx, usd = 1.0, A["start_usd"]
    else:
        fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
        usd = round(A["start_cad"] * fx, 2)
    return {"started": today_ny().isoformat(), "fx": fx, "start_usd": usd, "cash": usd,
            "positions": {}, "wins": 0, "losses": 0}


def record(state, kind, ticker, action, opt, price, pnl=None, note=""):
    """One move: trades.csv row, journal line, phone alert."""
    now = datetime.now(NY).strftime("%Y-%m-%d %H:%M")
    row = {"time_ny": now, "ticker": ticker, "action": action, "type": kind,
           "strike": opt.get("K", ""), "expiry": opt.get("exp", ""), "contracts": opt.get("qty", 1),
           "price": round(price, 2),
           "pnl_usd": "" if pnl is None else round(pnl, 2), "cash_usd": round(state["cash"], 2), "note": note}
    pnl_txt = ("" if pnl is None else f", P/L ${pnl:+.0f} USD"
               + (f" ({pnl / state['fx']:+.0f} CAD)" if A["currency"] == "CAD" else ""))
    qty = opt.get("qty", 1)
    line = (f"{action} {ticker} {f'{qty}x ' if qty > 1 else ''}${opt.get('K', '')} {kind} exp {opt.get('exp', '')} "
            f"at ${price:.2f}{pnl_txt}. {note}").strip()
    events.append((f"{A['short']}: {action} {ticker}", line, "high" if "ASSIGNED" in action else "default"))
    print(f"{now}  {line}")
    if DRY:
        return
    new = not os.path.exists(TRADES)
    with open(TRADES, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    if not os.path.exists(JOURNAL):
        open(JOURNAL, "w").write(f"# {A['title']}: journal\n\n")
    with open(JOURNAL, "a") as f:
        f.write(f"- **{now} NY** {line}\n")


def fill_sell(bid, ask):
    return (bid + (bid + ask) / 2) / 2


def fill_buy(bid, ask):
    return (ask + (bid + ask) / 2) / 2


def chain_row(tk, exp, kind, K):
    try:
        ch = tk.option_chain(exp)
    except Exception as error:
        print(f"{tk.ticker}: no option chain for {exp} ({error})")
        return None
    table = ch.puts if kind == "put" else ch.calls
    rows = table[table["strike"] == K]
    return rows.iloc[0] if len(rows) else None


def pick_expiry(tk, today, kind="put"):
    """The expiry inside the account's day range: the regular monthly (3rd Friday,
    most traded) if the account prefers it, otherwise the date closest to the ideal."""
    lo, hi, ideal = A["put_dte"] if kind == "put" else A["call_dte"]
    best = None
    for e in tk.options:
        d = date.fromisoformat(e)
        dte = (d - today).days
        if not lo <= dte <= hi:
            continue
        monthly = d.weekday() == 4 and 15 <= d.day <= 21
        score = (not monthly if A["prefer_monthly"] else False, abs(dte - ideal))
        if best is None or score < best[2]:
            best = (e, dte, score)
    return best[:2] if best else None


def earnings_before(tk, exp, today):
    try:
        dates = tk.calendar.get("Earnings Date", []) or []
    except Exception:
        return False
    return any(today <= d <= date.fromisoformat(exp) for d in dates)


def best_option(tk, S, exp, dte, kind, min_strike=0.0, max_strike=math.inf):
    """The liquid strike closest to the target delta, using Yahoo's implied vol."""
    try:
        ch = tk.option_chain(exp)
    except Exception:
        return None
    table = ch.puts if kind == "put" else ch.calls
    best = None
    for _, r in table.iterrows():
        K, bid, ask, iv, oi = r["strike"], r["bid"], r["ask"], r["impliedVolatility"], r["openInterest"]
        if not (min_strike <= K <= max_strike) or bid <= 0 or ask <= bid:
            continue
        if round(K * 2) != K * 2:       # odd strikes like 11.67 are adjusted contracts: skip
            continue
        mid = (bid + ask) / 2
        if (oi or 0) < R.MIN_OPEN_INTEREST or (ask - bid) > max(R.MAX_SPREAD * mid, 0.10) or not iv or iv < 0.05:
            continue
        if A["iv_cap"] and iv > A["iv_cap"]:
            continue
        delta = abs(R.bs_delta(S, K, dte / 365, iv, kind))
        gap = abs(delta - A["delta"])
        if delta <= A["delta"] + 0.08 and (best is None or gap < best["gap"]):
            best = {"K": float(K), "bid": float(bid), "ask": float(ask), "iv": float(iv),
                    "delta": delta, "gap": gap, "oi": int(oi)}
    return best


# ---------------- the daily run ----------------

def manage(state, closes, today):
    for t in list(state["positions"]):
        p = state["positions"][t]
        o = p.get("opt")
        tk = yf.Ticker(t)
        S = float(closes[t].dropna().iloc[-1])
        if o:
            exp = date.fromisoformat(o["exp"])
            if today > exp:
                # settle on the expiry-day close
                hist = closes[t].dropna()
                S_exp = float(hist[hist.index.date <= exp].iloc[-1])
                itm = S_exp < o["K"] if o["kind"] == "put" else S_exp > o["K"]
                q = o.get("qty", 1)
                if itm and o["kind"] == "put":
                    state["cash"] -= o["K"] * 100 * q
                    p["shares"], p["basis"] = 100 * q, o["K"] - o["credit"]
                    p["bought"], p["paid"] = o["exp"], o["K"]
                    p["first_put"] = o.get("opened", "")
                    record(state, "put", t, "ASSIGNED", o, o["K"],
                           note=f"Bought {100 * q} shares (stock closed ${S_exp:.2f}). Cost basis ${p['basis']:.2f}.")
                elif itm:
                    state["cash"] += o["K"] * 100 * q
                    pnl = (o["K"] - p["basis"]) * 100 * q
                    state["wins" if pnl >= 0 else "losses"] += 1
                    record(state, "call", t, "CALLED AWAY", o, o["K"], pnl, "Shares sold, slot is free.")
                    p["shares"] = 0
                else:
                    state["wins"] += 1
                    record(state, o["kind"], t, "EXPIRED", o, 0.0, (o["credit"] * 100 - R.FEE) * q,
                           "Expired worthless, kept the full premium.")
                p["opt"] = None
            else:
                r = chain_row(tk, o["exp"], o["kind"], o["K"])
                if r is not None and r["ask"] > 0:
                    cost = fill_buy(float(r["bid"]), float(r["ask"]))
                    dte = (exp - today).days
                    itm = S < o["K"] if o["kind"] == "put" else S > o["K"]
                    reason = None
                    if cost <= o["credit"] * A["tp"]:
                        reason = f"Hit {1 - A['tp']:.0%} profit."
                    elif A["time_exit"] is not None and dte <= A["time_exit"] and not itm:
                        reason = f"{dte} days left and out of the money."
                    if reason:
                        q = o.get("qty", 1)
                        state["cash"] -= (cost * 100 + R.FEE) * q
                        pnl = ((o["credit"] - cost) * 100 - 2 * R.FEE) * q
                        state["wins" if pnl >= 0 else "losses"] += 1
                        if o["kind"] == "call":
                            p["basis"] += cost      # undo the credit counted in the basis
                        p["opt"] = None
                        record(state, o["kind"], t, "BOUGHT BACK", o, cost, pnl, reason)
                    else:
                        o["mark"] = (float(r["bid"]) + float(r["ask"])) / 2
        if not p.get("shares") and not p.get("opt"):
            del state["positions"][t]
            continue
        # covered call on shares we own
        if p.get("shares") and not p.get("opt"):
            e = pick_expiry(tk, today, "call")
            if e:
                c = best_option(tk, S, e[0], e[1], "call", min_strike=p["basis"])
                if c:
                    credit = fill_sell(c["bid"], c["ask"])
                    if credit >= 0.05:
                        q = p["shares"] // 100
                        state["cash"] += (credit * 100 - R.FEE) * q
                        p["basis"] -= credit
                        p["opt"] = {"kind": "call", "K": c["K"], "exp": e[0], "credit": credit,
                                    "opened": today.isoformat(), "qty": q}
                        record(state, "call", t, "SOLD", p["opt"], credit,
                               note=f"Covered call, delta {c['delta']:.2f}, IV {c['iv']:.0%}. "
                                    f"Stock ${S:.2f}, cost basis now ${p['basis']:.2f}.")


def equity(state, closes):
    eq = state["cash"]
    for t, p in state["positions"].items():
        eq += p.get("shares", 0) * float(closes[t].dropna().iloc[-1])
        o = p.get("opt")
        if o:
            eq -= o.get("mark", o["credit"]) * 100 * o.get("qty", 1)
    return eq


def open_new(state, closes, today):
    eq = equity(state, closes)
    secured = sum(p["opt"]["K"] * 100 * p["opt"].get("qty", 1) for p in state["positions"].values()
                  if p.get("opt") and p["opt"]["kind"] == "put")
    free = state["cash"] - secured - A["cash_reserve"] * eq
    slot = eq * A["slot"]
    ideas = []
    for t in A["universe"]:
        if len(state["positions"]) + len(ideas) >= A["max_pos"] * 3:
            break
        if t in state["positions"] or t not in closes:
            continue
        hist = closes[t].dropna()
        if hist.empty:
            continue
        S = float(hist.iloc[-1])
        if S < A["min_price"] or S * 0.9 * 100 > slot:
            print(f"{t}: skipped, ${S:.2f} x 100 shares is too big for one slot (${slot:,.0f})")
            continue
        if A["trend_days"] and S <= float(hist.tail(A["trend_days"]).mean()):
            continue
        if A["uptrend_days"]:
            past = hist[hist.index.date <= today - timedelta(days=A["uptrend_days"])]
            if past.empty or S <= float(past.iloc[-1]):
                print(f"{t}: skipped, not up over the last ~1.5 years")
                continue
        tk = yf.Ticker(t)
        if A["max_pe"]:
            try:
                pe = tk.info.get("trailingPE")
            except Exception:
                pe = None
            if not pe or pe <= 0 or pe > A["max_pe"]:
                print(f"{t}: skipped, P/E {pe} is not between 0 and {A['max_pe']}")
                continue
        e = pick_expiry(tk, today)
        if not e:
            continue
        if A["skip_earnings"] and earnings_before(tk, e[0], today):
            print(f"{t}: skipped, earnings before {e[0]}")
            continue
        o = best_option(tk, S, e[0], e[1], "put", max_strike=slot / 100)
        if not o:
            continue
        credit = fill_sell(o["bid"], o["ask"])
        if credit < R.MIN_CREDIT or credit / o["K"] < A["min_yield30"] * e[1] / 30:
            continue
        ideas.append((credit / o["K"], t, e, o, credit, S))
    for _, t, e, o, credit, S in sorted(ideas, reverse=True):
        if len(state["positions"]) >= A["max_pos"]:
            break
        q = max(1, int(slot // (o["K"] * 100))) if A["multi_contracts"] else 1   # fill the slot, or 1 contract
        while q > 1 and o["K"] * 100 * q > free:
            q -= 1
        if o["K"] * 100 * q > free:
            continue
        state["cash"] += (credit * 100 - R.FEE) * q
        free -= o["K"] * 100 * q
        opt = {"kind": "put", "K": o["K"], "exp": e[0], "credit": credit, "opened": today.isoformat(), "qty": q}
        state["positions"][t] = {"shares": 0, "basis": 0.0, "opt": opt}
        record(state, "put", t, "SOLD", opt, credit,
               note=f"{q} cash-secured put{'s' if q > 1 else ''}, delta {o['delta']:.2f}, IV {o['iv']:.0%}, "
                    f"{e[1]} days. Stock ${S:.2f}. Ties up ${o['K'] * 100 * q:,.0f}.")


def short(d):
    return d[5:] if d else "-"


def holding_rows(state, closes):
    """Each open holding: what it is, when it was sold / bought, and its P/L now."""
    rows = []
    for t, p in sorted(state["positions"].items()):
        o = p.get("opt") or {}
        S = float(closes[t].dropna().iloc[-1])
        mark = o.get("mark", o.get("credit", 0.0)) if o else 0.0
        q = o.get("qty", 1) if o else 1
        if p.get("shares"):
            pnl = (S - p["basis"]) * p["shares"] - mark * 100 * q
            capital = p.get("paid", p["basis"]) * p["shares"]
            what = f"{p['shares']} shares" + (f" + {q} call ${o['K']:g}" if o else "")
            label = f"{t} shares (bought {short(p.get('bought'))})"
        else:
            pnl = ((o["credit"] - mark) * 100 - R.FEE) * q
            capital = o["K"] * 100 * q
            what = f"{q} put{'s' if q > 1 else ''} ${o['K']:g}"
            label = f"{t} put ${o['K']:g} (sold {short(o.get('opened'))})"
        rows.append({"ticker": t, "what": what, "label": label, "S": S, "o": o, "p": p, "mark": mark,
                     "pnl_usd": pnl, "pnl_cad": pnl / state["fx"], "pct": pnl / capital * 100})
    return rows


def write_summary(state, closes, today):
    eq = equity(state, closes)
    pnl = eq - state["start_usd"]
    hist = [h for h in state.setdefault("history", []) if h["date"] != today.isoformat()]
    hist.append({"date": today.isoformat(), "equity_usd": round(eq, 2), "start_usd": state["start_usd"]})
    state["history"] = hist
    rows = holding_rows(state, closes)
    secured = sum(p["opt"]["K"] * 100 * p["opt"].get("qty", 1) for p in state["positions"].values()
                  if p.get("opt") and p["opt"]["kind"] == "put")
    cur = A["currency"]
    start_label = f"${state['start_usd'] / state['fx']:,.0f} {cur}" if cur == "USD" else f"${A['start_cad']:,.0f} CAD"
    if not DRY:
        wheel_charts.save(FOLDER, hist, state["fx"], rows, cur, start_label)
    lines = [f"# {A['title']}", "",
             f"Updated {datetime.now(NY):%Y-%m-%d %H:%M} New York. Started {state['started']}.", "",
             "| | |", "|---|---|",
             f"| Account value | **${eq / state['fx']:,.0f} {cur}**" + (f" (${eq:,.0f} USD) |" if cur == "CAD" else " |"),
             f"| Up / down | **{pnl / state['fx']:+,.0f} {cur}** ({round(pnl / state['start_usd'] * 100, 1) + 0.0:+.1f}%) |",
             f"| Closed trades | {state['wins']} wins, {state['losses']} losses |",
             f"| Cash | ${state['cash'] / state['fx']:,.0f} {cur}, of which ${secured / state['fx']:,.0f} {cur} is set "
             f"aside to cover the puts |", "",
             "![Account profit / loss](value.svg)", "",
             "## What it holds now", "",
             "![Holdings profit / loss](holdings.svg)", "",
             "| Stock | Holding | Sold put on | Bought shares on | Got / paid | Option worth now | Stock now "
             f"| Expiry | Up / down {cur} | Up / down % |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        o, p = r["o"], r["p"]
        first_put = p.get("first_put") or o.get("opened", "")
        got = (f"paid ${p['paid']:.2f}/share" if p.get("shares") else f"got ${o['credit']:.2f}")
        lines.append(f"| {r['ticker']} | {r['what']} | {first_put or '-'} | {p.get('bought', '-') if p.get('shares') else '-'} "
                     f"| {got} | {'$%.2f' % r['mark'] if o else '-'} | ${r['S']:.2f} | {o.get('exp', '-')} "
                     f"| {'🟢' if r['pnl_cad'] >= 0 else '🔴'} {r['pnl_cad']:+,.0f} | {r['pct']:+.1f}% |")
    if not rows:
        lines.append("| (none yet) | | | | | | | | | |")
    lines += ["", "Prices from Yahoo Finance option chains. Paper only: no real orders. "
              f"Rules: agents/wheel_rules.py (account \"{ACCOUNT}\"). Every move: [journal.md](journal.md)."]
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
    tickers = sorted(set(A["universe"]) | set(state["positions"]))
    period = "2y" if A["uptrend_days"] else "3mo"
    closes = yf.download(tickers, period=period, progress=False)["Close"]
    manage(state, closes, today)
    open_new(state, closes, today)
    eq = write_summary(state, closes, today)
    print(f"\n{A['title']}: ${eq / state['fx']:,.0f} {A['currency']}, {len(state['positions'])} positions.")
    if DRY:
        print("(dry run: nothing saved, no phone alerts)")
        return
    json.dump(state, open(STATE, "w"), indent=1)
    for title, msg, prio in events:
        # the Ryan comparison account is pretend money: its alerts arrive quietly
        send(title, msg, priority=prio if ACCOUNT == "ours" else "low", tags="money_with_wings")


if __name__ == "__main__":
    main()
