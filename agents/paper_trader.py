"""
paper_trader.py - Agent #6: paper trades every session with your exact rules
and keeps score, including a practice prop firm challenge.

Run it like this (from the project folder, with PYTHONPATH set to "."):
    python agents/paper_trader.py            (both markets)
    python agents/paper_trader.py nasdaq     (one market)

It runs every 15 minutes during the sessions. Each time, it loads the real
5-minute candles, applies the rules in main.py (key levels from the 2 hours
before the open, 60-minute window, confirming
candle, 3 targets, stop to Target 1 after Target 2, close at the session end),
and records a session as soon as its outcome is known:
  - a trade, once it has fully closed (all targets, the stop, or session end)
  - no trade, once the entry window has passed without a confirmed breakout
It never records a session twice.

It writes, in paper-trading/:
  trades.csv         one row per session, the raw record
  paper-journal.md   a journal entry for every paper trade
  summary.md         totals, profitable days, and the challenge simulation

THE CHALLENGE SIMULATION replays the paper results against the prop firm
rules in CHALLENGE, as back-to-back attempts: each attempt runs until it
passes or fails, and the next one starts the following trading day.

It places NO orders and has no broker access. The live version on
TradingView is tradingview/breakout_strategy.pine; compare the two.
"""

import csv
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import main as rules                       # the replay engine (main.py)
from data import SYMBOLS, load_from_yahoo
from notify import send
from trade_review import draw, review, tradingview_link

# ---------------- SETTINGS ----------------
FOLDER = "paper-trading"
TRADES_CSV = os.path.join(FOLDER, "trades.csv")
JOURNAL = os.path.join(FOLDER, "paper-journal.md")
SUMMARY = os.path.join(FOLDER, "summary.md")
LOOKBACK = "7d"                 # how much recent data to check for unrecorded sessions
MIN_SHARE_OF_CANDLES = 0.8      # skip a session with too much missing data (retry later)
COMMISSION_PER_CONTRACT = 1.00  # round-trip fees per micro contract, in dollars
GOAL_TRADING_DAYS = 20          # paper trade at least this many days before a prop demo
START_DAY = "2026-10-19"        # first trading day of the paper record (sessions before
                                # it are backtest territory, see main.py)
# Max drawdown: main.MAX_DRAWDOWN ($4,000). Once hit, no more paper trades are
# taken. To start a fresh account after that, set this to the first trading
# day of the new account, like "2026-11-02".
DRAWDOWN_RESET_DAY = None

# Practice challenge. These match Tradeify's GROWTH 50K evaluation as described
# in its help center in October 2026. Prop firms change their rules, so check
# help.tradeify.co and update these before you rely on them.
CHALLENGE = {
    "name": "Tradeify Growth 50K (practice)",
    "start_balance": 50000,
    "profit_target": 3000,
    "trailing_drawdown": 2000,   # trails the highest end-of-day balance
    "daily_loss_limit": 1250,    # soft limit: stop trading for the day
}
# ------------------------------------------

FIELDS = ["trading_day", "instrument", "session_start", "signal", "direction",
          "entry_time", "entry", "stop", "exit_time", "average_exit", "contracts",
          "gross", "fees", "net", "events", "sell_plan", "key_high", "key_low",
          "fills", "best_move", "worst_move", "lessons", "chart"]
CHART_FOLDER = os.path.join(FOLDER, "charts")
OPEN_TRADES = os.path.join(FOLDER, "open-trades.json")


trading_day = rules.trading_day


def apply_max_drawdown(rows, added):
    """Replay the balance in time order. New sessions after the max drawdown
    was hit become 'stopped' rows: the trade is not taken. Returns the day it
    was hit, or None."""
    account = rules.Account()
    new = {id(r) for r in added}
    for r in sorted(rows, key=lambda r: r["session_start"]):
        if DRAWDOWN_RESET_DAY and r["trading_day"] < DRAWDOWN_RESET_DAY:
            continue
        start = datetime.strptime(r["session_start"], "%Y-%m-%d %H:%M")
        if not account.can_trade(start):
            if id(r) in new:
                r.update({"signal": "stopped", "direction": "", "entry_time": "",
                          "entry": "", "stop": "", "exit_time": "", "average_exit": "",
                          "contracts": 0, "gross": 0.0, "fees": 0.0, "net": 0.0,
                          "events": f"Not taken: the ${rules.MAX_DRAWDOWN:,} max drawdown "
                                    f"was hit on {account.stopped_on}."})
            continue
        if r["signal"] == "yes":
            account.record(float(r["net"]))
    return account.stopped_on


def read_rows():
    try:
        with open(TRADES_CSV, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def new_sessions(instrument, candles, recorded, now, open_now=None):
    """Rows for sessions whose outcome is known and not in trades.csv yet."""
    config = rules.SESSIONS[instrument]
    sessions = rules.group_into_sessions(candles, config)
    starts = list(sessions)
    everything = rules.timeline(candles)
    expected = config["minutes"] / 5
    rows = []
    for i, start in enumerate(starts[1:], 1):
        key = (instrument, f"{start:%Y-%m-%d %H:%M}")
        if key in recorded:
            continue
        levels = rules.key_levels_for(sessions, starts, i, config, everything)
        if levels is None:
            continue
        if trading_day(start).isoformat() < START_DAY:
            continue
        finished = start + timedelta(minutes=config["minutes"]) <= now
        if finished and len(sessions[start]) < MIN_SHARE_OF_CANDLES * expected:
            print(f"{instrument} {start}: only {len(sessions[start])} candles, will retry later")
            continue
        session = sessions[start]
        if not finished:
            # Only use candles that have closed; the newest one may still be forming.
            session = [(t, c) for t, c in session if t + timedelta(minutes=5) <= now]
            if not session:
                continue
        key_high, key_low = levels
        result = rules.play_session(instrument, config, start, session,
                                    key_high, key_low)
        if not finished:
            last_candle = session[-1][0]
            if result is None:
                # The last breakout candle and its confirming candle must be in.
                window_end = start + timedelta(minutes=rules.ENTRY_WINDOW_MINUTES)
                if last_candle < window_end:
                    continue   # the entry window is not over yet
            elif any("session ended" in text for _, text in result["events"]):
                if open_now is not None:   # the trade is still open: show it
                    open_now[f"{instrument} {key[1]}"] = {
                        "instrument": instrument, "session_start": key[1],
                        "direction": result["direction"], "contracts": result["contracts"],
                        "entry": result["entry"], "entry_time": f"{result['entry_time']:%H:%M}",
                        "stop": result["stop"], "sell_plan": result["sell_plan"],
                        "sold_so_far": [f for f in result["fills"]
                                        if f["what"] != "Session end"]}
                continue
        row = {"trading_day": trading_day(start).isoformat(), "instrument": instrument,
               "session_start": key[1], "signal": "no", "direction": "", "entry_time": "",
               "entry": "", "stop": "", "exit_time": "", "average_exit": "",
               "contracts": 0, "gross": 0.0, "fees": 0.0, "net": 0.0,
               "events": f"No confirmed breakout in the first {rules.ENTRY_WINDOW_MINUTES} "
                         f"minutes. Key high {key_high:.2f}, low {key_low:.2f}.",
               "key_high": round(key_high, 2), "key_low": round(key_low, 2)}
        if result:
            result["session_start"] = start
            facts = review(result, session)
            chart = os.path.join(CHART_FOLDER, f"{key[1][:10]}-{instrument}.svg")
            draw(result, everything, chart)
            fees = round(result["contracts"] * COMMISSION_PER_CONTRACT, 2)
            row.update({
                "signal": "yes", "direction": result["direction"],
                "entry_time": f"{result['entry_time']:%H:%M}", "entry": result["entry"],
                "stop": result["stop"], "exit_time": f"{result['exit_time']:%H:%M}",
                "average_exit": result["average_exit"], "contracts": result["contracts"],
                "gross": result["profit"], "fees": fees,
                "net": round(result["profit"] - fees, 2),
                "events": "; ".join(f"{t:%H:%M} {text}" for t, text in result["events"]),
                "sell_plan": "/".join(str(n) for n in result["sell_plan"]),
                "fills": json.dumps(result["fills"]),
                "best_move": facts["mfe"], "worst_move": facts["mae"],
                "lessons": " | ".join(facts["lessons"]),
                "chart": chart,
            })
        rows.append(row)
    return rows


def fills_of(row):
    try:
        return json.loads(row.get("fills") or "[]")
    except ValueError:
        return []


def journal_entry(row):
    name = rules.SESSIONS[row["instrument"]]["name"]
    level = "high" if row["direction"] == "long" else "low"
    net = float(row["net"])
    side = "Bought" if row["direction"] == "long" else "Sold short"
    out = [
        f"### {'✅' if net > 0 else '❌'} {row['trading_day']} | {name} | "
        f"{row['direction'].capitalize()} | {money(net)}",
        f"- **Session start (New York):** {row['session_start']}",
        f"- **Why:** two 5-minute candles closed beyond the key {level} "
        f"({row.get('key_high') if row['direction'] == 'long' else row.get('key_low')})",
        f"- **Entry:** {side} **{row['contracts']} contracts** at **{row['entry']}** "
        f"at **{row['entry_time']}** (sell plan {row.get('sell_plan') or 'n/a'})",
        f"- **Stop:** {row['stop']}",
    ]
    fills = fills_of(row)
    if fills:
        out += ["", "| Time | What | Contracts | Price | Profit |", "|---|---|---|---|---|"]
        out += [f"| {f['time']} | {f['what']} | {f['contracts']} | {f['price']} | "
                f"{money(f['profit'])} |" for f in fills]
        out.append("")
    out += [
        f"- **Exit:** last contract out at **{row['exit_time']}**, average {row['average_exit']}",
        f"- **Result:** {money(float(row['gross']))} before fees, **{money(net)} after fees**",
        f"- **What could have gone better:**",
    ]
    out += [f"  - {text}" for text in (row.get("lessons") or "").split(" | ") if text]
    if row.get("chart"):
        out += ["", f"![Chart of this trade](charts/{os.path.basename(row['chart'])})"]
    out += [f"", f"[Open {name} on TradingView]({tradingview_link(row['instrument'])}) "
            f"(add tradingview/breakout_strategy.pine to see this trade marked)",
            "", "---", ""]
    return "\n".join(out)


def build_journal(rows, stopped_on=None):
    """The whole journal, rebuilt from trades.csv each run, ending with totals."""
    trades = [r for r in rows if r["signal"] == "yes"]
    out = ["# Paper trading journal", "",
           "Written automatically by paper_trader.py as each paper trade closes. "
           "Nothing here is a real trade.", "", "---", ""]
    out += [journal_entry(r) for r in reversed(trades)]   # newest first
    nets = [float(r["net"]) for r in trades]
    wins = [n for n in nets if n > 0]
    out += ["## Total", ""]
    if not trades:
        out += [f"No paper trades yet. The record starts on {START_DAY}.", ""]
        return "\n".join(out)
    out += [f"- **Total profit / loss after fees:** **{money(sum(nets))}** "
            f"over {len(trades)} trades",
            f"- **Winners:** {len(wins)} ({len(wins) / len(nets):.0%}), "
            f"**losers:** {len(nets) - len(wins)}",
            f"- **Before fees:** {money(sum(float(r['gross']) for r in trades))}, "
            f"fees paid: {money(sum(float(r['fees']) for r in trades))}"]
    for name in rules.SESSIONS:
        mine = [float(r["net"]) for r in trades if r["instrument"] == name]
        out.append(f"- **{rules.SESSIONS[name]['name']}:** {money(sum(mine))} over {len(mine)} trades")
    if stopped_on:
        out.append(f"- ⛔ The ${rules.MAX_DRAWDOWN:,} max drawdown was hit on {stopped_on}.")
    return "\n".join(out + [""])


def by_day(rows):
    days = {}
    for r in sorted(rows, key=lambda r: r["session_start"]):
        days.setdefault(r["trading_day"], []).append(r)
    return days


def simulate_challenge(days):
    """Back-to-back attempts. Returns a list of attempt dictionaries."""
    c = CHALLENGE
    attempts, current = [], None
    for day, sessions in days.items():
        if current is None:
            current = {"start": day, "balance": c["start_balance"],
                       "peak_eod": c["start_balance"], "days": 0, "result": "In progress",
                       "end": day, "note": "", "dll_days": 0}
        floor = current["peak_eod"] - c["trailing_drawdown"]
        day_net, traded = 0.0, False
        for r in sessions:
            if r["signal"] != "yes":
                continue
            if day_net <= -c["daily_loss_limit"]:
                current["note"] = "skipped a session after the daily loss limit"
                continue
            day_net += float(r["net"])
            traded = True
            if current["balance"] + day_net <= floor:
                current["result"] = "Failed"
                current["note"] = (f"balance fell to ${current['balance'] + day_net:,.0f}, "
                                   f"below the drawdown floor of ${floor:,.0f}")
                break
        if day_net <= -c["daily_loss_limit"]:
            current["dll_days"] += 1
        current["balance"] += day_net
        current["days"] += 1 if traded else 0
        current["end"] = day
        if current["result"] == "In progress":
            current["peak_eod"] = max(current["peak_eod"], current["balance"])
            if current["balance"] >= c["start_balance"] + c["profit_target"]:
                current["result"] = "Passed"
        if current["result"] != "In progress":
            attempts.append(current)
            current = None
    if current is not None:
        attempts.append(current)
    return attempts


def money(value):
    return f"-${-value:,.0f}" if value < 0 else f"${value:,.0f}"


def build_summary(rows, now, stopped_on=None):
    trades = [r for r in rows if r["signal"] == "yes"]
    nets = [float(r["net"]) for r in trades]
    wins = [n for n in nets if n > 0]
    losses = [n for n in nets if n < 0]
    days = by_day(rows)
    day_nets = {d: sum(float(r["net"]) for r in s) for d, s in days.items()}
    traded_days = {d: n for d, n in day_nets.items()
                   if any(r["signal"] == "yes" for r in days[d])}
    profitable = sum(1 for n in traded_days.values() if n > 0)

    equity, peak, max_dd = 0.0, 0.0, 0.0
    for d in days:
        equity += day_nets[d]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    if not rows:
        return ("# Paper trading summary\n\n"
                f"*Updated {now:%Y-%m-%d %H:%M} New York time.*\n\n"
                f"No sessions recorded yet. The paper record starts on {START_DAY}.\n")
    out = ["# Paper trading summary", "",
           f"*Updated {now:%Y-%m-%d %H:%M} New York time. Paper results from real "
           "5-minute candles with perfect fills at target and stop prices, after "
           f"${COMMISSION_PER_CONTRACT:.2f} per contract in fees. Real fills can be worse.*", "",
           "## At a glance", ""]
    if stopped_on:
        out += [f"⛔ **The ${rules.MAX_DRAWDOWN:,} max drawdown was hit on {stopped_on}. "
                "No more paper trades are taken until the account is reset** "
                "(DRAWDOWN_RESET_DAY in agents/paper_trader.py).", ""]
    out += [
           f"- Total after fees: **{money(sum(nets))}** over {len(trades)} trades "
           f"({len(rows)} sessions watched)",
           f"- Trading days with a trade: **{len(traded_days)}**, profitable: "
           f"**{profitable}**, losing: {len(traded_days) - profitable}",
           f"- Win rate: {len(wins) / len(nets) * 100:.0f}%" if nets else "- Win rate: n/a",
           f"- Profit factor: {sum(wins) / -sum(losses):.2f}" if losses else
           "- Profit factor: n/a (no losing trades yet)",
           f"- Biggest drop from a high (max drawdown): {money(max_dd)}",
           f"- Room left before the {money(rules.MAX_DRAWDOWN)} max drawdown: "
           f"**{money(max(0, rules.MAX_DRAWDOWN - (peak - equity)))}**",
           f"- Progress toward a prop demo: **{len(traded_days)} of {GOAL_TRADING_DAYS}** "
           "trading days", ""]

    out += ["## By market", "", "| Market | Trades | Wins | Total after fees |",
            "|---|---|---|---|"]
    for name in rules.SESSIONS:
        mine = [float(r["net"]) for r in trades if r["instrument"] == name]
        out.append(f"| {name} | {len(mine)} | {sum(1 for n in mine if n > 0)} | "
                   f"{money(sum(mine))} |")

    c = CHALLENGE
    attempts = simulate_challenge(days)
    passed = sum(1 for a in attempts if a["result"] == "Passed")
    failed = sum(1 for a in attempts if a["result"] == "Failed")
    out += ["", f"## Challenge simulation: {c['name']}", "",
            f"Rules: reach {money(c['profit_target'])} profit before the balance drops "
            f"{money(c['trailing_drawdown'])} below its highest end-of-day balance. "
            f"Stop for the day after losing {money(c['daily_loss_limit'])}. "
            "Check the firm's current rules before relying on this.", "",
            f"**Passed {passed}, failed {failed}, "
            f"{len(attempts) - passed - failed} in progress.**", "",
            "| Attempt | Started | Ended | Trading days | Balance | Result | Note |",
            "|---|---|---|---|---|---|---|"]
    for i, a in enumerate(attempts, 1):
        out.append(f"| {i} | {a['start']} | {a['end']} | {a['days']} | "
                   f"{money(a['balance'])} | {a['result']} | {a['note']} |")

    out += ["", "## Daily results", "", "| Trading day | Sessions | Result after fees |",
            "|---|---|---|"]
    for d in list(days)[::-1][:30]:
        what = ", ".join(f"{r['instrument']} {r['direction'] or ('stopped by max drawdown' if r['signal'] == 'stopped' else 'no trade')}" for r in days[d])
        out.append(f"| {d} | {what} | {money(day_nets[d])} |")
    out += ["", f"[Every paper trade](paper-journal.md) · [Raw data](trades.csv)", ""]
    return "\n".join(out)


def save_open_trades(open_now):
    """paper-trading/open-trades.json: trades entered but not finished yet.
    Sends one phone alert when a trade is first entered."""
    try:
        before = json.load(open(OPEN_TRADES))
    except (OSError, ValueError):
        before = {}
    for key, t in open_now.items():
        if key not in before:
            send(f"{rules.SESSIONS[t['instrument']]['name']} paper trade entered",
                 f"{t['direction'].capitalize()} {t['contracts']} contracts at {t['entry']} "
                 f"({t['entry_time']} New York), stop {t['stop']}.",
                 priority="high", tags="rocket",
                 link="https://github.com/jayryd7-gif/ai-trading-agent/blob/main/DASHBOARD.md")
    with open(OPEN_TRADES, "w") as f:
        json.dump(open_now, f, indent=1)


def alert_phone(rows, added, new_trades):
    """Phone alerts: every closed paper trade, and the max drawdown being hit."""
    total = sum(float(r["net"]) for r in rows if r["signal"] == "yes")
    for r in new_trades:
        net = float(r["net"])
        send(f"{rules.SESSIONS[r['instrument']]['name']} paper trade: {money(net)}",
             f"{r['direction'].capitalize()} {r['contracts']} at {r['entry']} ({r['entry_time']}), "
             f"closed {r['exit_time']}. {money(net)} after fees. Paper total so far: "
             f"{money(total)}. Tap for the fills and the chart.",
             priority="high", tags="chart_with_upwards_trend" if net > 0 else "chart_with_downwards_trend",
             link="https://github.com/jayryd7-gif/ai-trading-agent/blob/main/paper-trading/paper-journal.md")
    if any(r["signal"] == "stopped" for r in added) and \
            not any(r["signal"] == "stopped" for r in rows if r not in added):
        send("Max drawdown hit: paper trading stopped",
             f"The ${rules.MAX_DRAWDOWN:,} max drawdown was reached. No more paper trades until "
             "the account is reset.", priority="urgent", tags="rotating_light")


def main(argv=None, now=None):
    argv = sys.argv[1:] if argv is None else argv
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    instruments = [a for a in argv if a in rules.SESSIONS] or list(rules.SESSIONS)

    rows = read_rows()
    recorded = {(r["instrument"], r["session_start"]) for r in rows}
    added, open_now = [], {}
    for instrument in instruments:
        try:
            candles = load_from_yahoo(SYMBOLS[instrument], interval="5m", period=LOOKBACK)
        except Exception as error:
            print(f"Could not load {instrument} data: {error}")
            continue
        added += new_sessions(instrument, candles, recorded, now, open_now)

    os.makedirs(FOLDER, exist_ok=True)
    rows = sorted(rows + added, key=lambda r: r["session_start"])
    stopped_on = apply_max_drawdown(rows, added)
    with open(TRADES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, restval="", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    new_trades = [r for r in added if r["signal"] == "yes"]
    with open(JOURNAL, "w") as f:
        f.write(build_journal(rows, stopped_on))

    with open(SUMMARY, "w") as f:
        f.write(build_summary(rows, now, stopped_on))

    alert_phone(rows, added, new_trades)
    save_open_trades(open_now)
    print(f"Recorded {len(added)} new session(s), {len(new_trades)} with a trade.")
    for r in added:
        print(f"  {r['session_start']} {r['instrument']}: "
              f"{r['direction'] or ('stopped by max drawdown' if r['signal'] == 'stopped' else 'no trade')} {money(float(r['net']))}")
    print(f"Saved {SUMMARY}")


if __name__ == "__main__":
    main()
