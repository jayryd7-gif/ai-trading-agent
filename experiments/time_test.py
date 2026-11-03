"""
time_test.py - Which session start times make the most money?

Replays the bot (same rules, same stops and targets) with different gold start
times, with and without the early clear-breakout entries, on the last 30 and
60 days of 5-minute candles, for two accounts:
  - PAPER: the paper bot on the Tradeify practice account (1/2/2 contracts,
    $1,250 daily loss limit), like paper_trader.py and the RESEARCH script.
  - LIVE: the LIVE 50K script's rules (run_live): Tradeify Select 50K
    ($2,000 end-of-day trailing drawdown, $3,000 target, 40% consistency,
    3 days minimum), 2/2/2 contracts, else 1/1/1, else 1 contract to Target 3,
    $800 most each chart may lose a day, $300 kept above the floor on every
    stop, no trades under $700 of room, done for the day under $1,000, and the
    gold chart counting the Nasdaq chart's $800 as already lost. After a pass
    or a breach a new evaluation starts, like the script's replay.

Run from the project folder (takes a few minutes):
    python3 experiments/time_test.py
Add more options to OPTIONS to test other times or sessions.

A replay has perfect fills, and picking the best of many options on 30 days
partly picks luck. Trust an option more when it also wins on 60 days and in
both halves.
"""
import os
import pickle
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents")]

import main as R
import tradeify
from data import SYMBOLS, load_from_yahoo

CACHE = os.path.join(ROOT, "experiments", ".time_test_candles.pkl")
TOKYO = {"open": (9, 0), "zone": "Asia/Tokyo"}

# (label, gold session, early-watch minutes before each open)
OPTIONS = [("Before today: Tokyo open (7 PM now), no early", TOKYO, 0)]
for hour, minute in ((18, 0), (19, 0), (19, 30), (20, 0), (20, 30), (21, 0), (21, 30),
                     (22, 0), (3, 0)):
    name = datetime(2000, 1, 1, hour, minute).strftime("%-I:%M %p")
    OPTIONS.append((f"Gold {name}, no early", {"open": (hour, minute)}, 0))
    OPTIONS.append((f"Gold {name} + early 90 min", {"open": (hour, minute)}, 90))
OPTIONS.append(("Tokyo open + early 90 min", TOKYO, 90))
for hour in (20, 22):
    OPTIONS.append((f"Gold {hour - 12}:00 PM + early 90 min on gold only", {"open": (hour, 0)},
                    "gold"))

# early "gold": the early watch on gold only (Nasdaq waits for 9:30)


def candles():
    """Both markets' 5-minute candles, saved so reruns are quick."""
    if os.path.exists(CACHE) and \
            datetime.now().timestamp() - os.path.getmtime(CACHE) < 12 * 3600:
        with open(CACHE, "rb") as f:
            return pickle.load(f)
    data = {k: load_from_yahoo(SYMBOLS[k], "5m", "60d") for k in R.SESSIONS}
    with open(CACHE, "wb") as f:
        pickle.dump(data, f)
    return data


LIVE = {"start": 50000, "drawdown": 2000, "target": 3000, "consistency": 0.40,
        "min_days": 3, "day_stop": 800, "buffer": 300, "pause_below": 700,
        "stop_day_below": 1000, "plans": ([2, 2, 2], [1, 1, 1], [0, 0, 1])}


NASDAQ_LEVELS = [None]   # None, ("pre", minutes) or ("range", minutes): see nasdaq_levels


def nasdaq_levels(everything, start, session):
    """Other Nasdaq key levels to test: ("pre", m) = the high and low of the m
    minutes before 9:30; ("range", m) = the opening range, the first m minutes
    after 9:30, with entries looked for from then on.
    Returns (levels, session, start) or None."""
    kind, m = NASDAQ_LEVELS[0]
    if kind == "pre":
        pre = [c for t, c in everything if start - timedelta(minutes=m) <= t < start]
        if len(pre) < m / 10:
            return None
        return R.find_key_levels(pre), session, start
    cut = start + timedelta(minutes=m)
    first = [c for t, c in session if t < cut]
    if len(first) < m / 5:
        return None
    return R.find_key_levels(first), [(t, c) for t, c in session if t >= cut], cut


def run_live(cut):
    """The LIVE 50K script's rules on both markets as one real account.
    Returns (trades, passes, breaches)."""
    L = LIVE
    plan = []
    for instrument, candles in cut.items():
        config = R.SESSIONS[instrument]
        sessions = R.group_into_sessions(candles, config)
        starts = list(sessions)
        everything = R.timeline(candles)
        for i in range(1, len(starts)):
            if instrument == "nasdaq" and NASDAQ_LEVELS[0]:
                found = nasdaq_levels(everything, starts[i], sessions[starts[i]])
                if found:
                    levels, play, play_start = found
                    plan.append((play_start, instrument, play, *levels, None))
                continue
            levels = R.key_levels_for(sessions, starts, i, config, everything)
            if levels is not None:
                plan.append((starts[i], instrument,
                             R.with_early(everything, starts[i], sessions[starts[i]], config),
                             *levels, R.early_levels(everything, starts[i], config)))
    bal, peak, best, days = L["start"], L["start"], 0.0, 0
    passes = breaches = 0
    pass_days, eval_start = [], None
    day, day_pnl, day_over = None, {}, {}
    trades = []

    def close_day():
        nonlocal bal, peak, best, days, passes
        if day is None:
            return
        total = sum(day_pnl.values())
        if day_pnl:
            days += 1
            best = max(best, total)
        peak = max(peak, bal)
        profit = bal - L["start"]
        if profit >= L["target"] and best <= L["consistency"] * profit and days >= L["min_days"]:
            passes += 1
            pass_days.append((eval_start, day))
            fresh()

    def fresh():
        nonlocal bal, peak, best, days
        nonlocal eval_start
        bal, peak, best, days = L["start"], L["start"], 0.0, 0
        eval_start = None

    for start, instrument, session, key_high, key_low, early in sorted(plan, key=lambda p: p[0]):
        today = R.trading_day(start)
        if today != day:
            close_day()
            day, day_pnl, day_over = today, {}, {}
        unseen = L["day_stop"] if instrument == "gold" else 0
        cushion = bal - (peak - L["drawdown"])
        mine = day_pnl.get(instrument)
        if (day_over.get(instrument) or (mine or 0) <= -L["day_stop"]
                or cushion - unseen < L["pause_below"]):
            continue
        allowance = min(cushion - unseen - L["buffer"], L["day_stop"] + (mine or 0))
        result = None
        for size in L["plans"]:
            r = R.play_session(instrument, R.SESSIONS[instrument], start, session, key_high,
                               key_low, size_plan=size, max_loss=allowance, early=early)
            if r is None:
                break
            if r["risk_dollars"] < allowance:
                result = r
                break
        if result is None:
            continue
        net = result["profit"] - 0.5 * result["contracts"]
        if bal - result["worst_dollars"] <= peak - L["drawdown"]:
            net = (peak - L["drawdown"]) - bal          # closed at the floor: breached
        bal += net
        day_pnl[instrument] = (mine or 0) + net
        result["start"] = start
        eval_start = eval_start or today
        trades.append((result, net))
        if bal <= peak - L["drawdown"]:
            breaches += 1
            fresh()
        elif bal - (peak - L["drawdown"]) - unseen < L["stop_day_below"]:
            day_over[instrument] = True
    close_day()
    run_live.pass_days = pass_days
    return trades, passes, breaches


def run(data, gold, early, days, live):
    R.SESSIONS["gold"] = {"label": "Asia", "minutes": 480, "name": "Gold (MGC)", **gold,
                          "early": 90 if early == "gold" else early}
    R.SESSIONS["nasdaq"]["early"] = 0 if early == "gold" else early
    last = max(R.parse_time(c.time) for c in data["nasdaq"])
    since = (last - timedelta(days=days + 1)).strftime("%Y-%m-%d %H:%M")
    cut = {k: [c for c in v if c.time >= since] for k, v in data.items()}
    first = (last - timedelta(days=days)).date()
    if live:
        done, passed, failed = run_live(cut)
        done = [(r, n) for r, n in done if r["start"].date() >= first]
        trades, net = [r for r, _ in done], [n for _, n in done]
    else:
        account = tradeify.TradeifyAccount()
        results, _ = R.run_account(cut, account)
        attempts = account.finish()
        passed = sum(a["result"] == "Passed" for a in attempts)
        failed = sum(a["result"] == "Failed" for a in attempts)
        trades = [r for r in results if r["start"].date() >= first]
        net = [r["profit"] - R.contracts_traded(r) for r in trades]
    gold_net = sum(n for r, n in zip(trades, net) if r["instrument"] == "gold")
    days_pnl = {}
    for r, n in zip(trades, net):
        d = R.trading_day(r["start"])
        days_pnl[d] = days_pnl.get(d, 0) + n
    half = first + timedelta(days=days // 2)
    wins = sum(n for n in net if n > 0)
    losses = -sum(n for n in net if n < 0) or 1
    return {
        "net": sum(net), "gold": gold_net, "nasdaq": sum(net) - gold_net,
        "trades": len(net), "won": sum(n > 0 for n in net), "pf": wins / losses,
        "worst": min(days_pnl.values(), default=0),
        "first_half": sum(n for d, n in days_pnl.items() if d < half),
        "second_half": sum(n for d, n in days_pnl.items() if d >= half),
        "passed": passed,
        "failed": failed,
        "early": sum(1 for r in trades if r.get("early")),
    }


def money(v):
    return f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"


def row(label, a, b):
    return (f"| {label} | **{money(a['net'])}** | {money(a['gold'])} | {money(a['nasdaq'])} | "
            f"{a['won']}/{a['trades']} | {a['pf']:.2f} | {money(a['worst'])} | "
            f"{money(a['first_half'])} / {money(a['second_half'])} | {a['passed']}/{a['failed']} | "
            f"{money(b['net'])} | {money(b['gold'])} | {b['passed']}/{b['failed']} |")


if __name__ == "__main__":
    data = candles()
    head = ("| Option | 30 days | gold | Nasdaq | won | PF | worst day | halves | "
            "evals pass/fail | 60 days | gold 60d | evals 60d |\n" + "|---" * 12 + "|")
    for live in [x for x in (True, False) if not sys.argv[1:] or sys.argv[1] == ("live" if x else "paper")]:
        print(f"\n### {'LIVE 50K rules' if live else 'PAPER (research) account'}\n\n{head}")
        for label, gold, early in OPTIONS:
            print(row(label, run(data, gold, early, 30, live), run(data, gold, early, 60, live)),
                  flush=True)
