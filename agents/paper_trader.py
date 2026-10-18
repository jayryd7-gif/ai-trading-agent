"""
paper_trader.py - Agent #6: paper trades every session with your exact rules
and keeps score, including a practice prop firm challenge.

Run it like this (from the project folder, with PYTHONPATH set to "."):
    python agents/paper_trader.py            (both markets)
    python agents/paper_trader.py nasdaq     (one market)

It runs every 15 minutes during the sessions. Each time, it loads the real
5-minute candles, applies the rules in main.py (30-minute window, confirming
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
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import main as rules                       # the replay engine (main.py)
from data import SYMBOLS, load_from_yahoo
from key_levels import find_key_levels

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
          "gross", "fees", "net", "events"]


def trading_day(start):
    """Futures trading days start at 6 PM New York, so an evening session
    (gold at the Tokyo open) belongs to the next day."""
    return (start + timedelta(days=1)).date() if start.hour >= 18 else start.date()


def read_rows():
    try:
        with open(TRADES_CSV, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def new_sessions(instrument, candles, recorded, now):
    """Rows for sessions whose outcome is known and not in trades.csv yet."""
    config = rules.SESSIONS[instrument]
    sessions = rules.group_into_sessions(candles, config)
    starts = list(sessions)
    expected = config["minutes"] / 5
    rows = []
    for i, start in enumerate(starts[1:], 1):
        prev = rules.previous_full_session(sessions, starts, i, config)
        key = (instrument, f"{start:%Y-%m-%d %H:%M}")
        if key in recorded or prev is None:
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
        key_high, key_low = find_key_levels([c for _, c in sessions[prev]])
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
                continue       # the trade is still open
        row = {"trading_day": trading_day(start).isoformat(), "instrument": instrument,
               "session_start": key[1], "signal": "no", "direction": "", "entry_time": "",
               "entry": "", "stop": "", "exit_time": "", "average_exit": "",
               "contracts": 0, "gross": 0.0, "fees": 0.0, "net": 0.0,
               "events": f"No confirmed breakout. Previous high {key_high:.2f}, low {key_low:.2f}."}
        if result:
            fees = round(result["contracts"] * COMMISSION_PER_CONTRACT, 2)
            row.update({
                "signal": "yes", "direction": result["direction"],
                "entry_time": f"{result['entry_time']:%H:%M}", "entry": result["entry"],
                "stop": result["stop"], "exit_time": f"{result['exit_time']:%H:%M}",
                "average_exit": result["average_exit"], "contracts": result["contracts"],
                "gross": result["profit"], "fees": fees,
                "net": round(result["profit"] - fees, 2),
                "events": "; ".join(f"{t:%H:%M} {text}" for t, text in result["events"]),
            })
        rows.append(row)
    return rows


def journal_entry(row):
    name = rules.SESSIONS[row["instrument"]]["name"]
    level = "high" if row["direction"] == "long" else "low"
    return "\n".join([
        f"### Paper trade | {row['trading_day']} | {name}",
        f"- **Session start (New York):** {row['session_start']}",
        f"- **Signal:** {row['direction'].capitalize()} after two candles closed beyond "
        f"the previous session {level}",
        f"- **Entry:** {row['entry']} at {row['entry_time']}, stop {row['stop']}, "
        f"{row['contracts']} contracts",
        f"- **Exit:** average {row['average_exit']}, last fill at {row['exit_time']}",
        f"- **Result:** {money(float(row['gross']))} before fees, "
        f"**{money(float(row['net']))} after fees**",
        f"- **How it went:** {row['events']}",
        "", "---", ""])


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


def build_summary(rows, now):
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
           "## At a glance", "",
           f"- Total after fees: **{money(sum(nets))}** over {len(trades)} trades "
           f"({len(rows)} sessions watched)",
           f"- Trading days with a trade: **{len(traded_days)}**, profitable: "
           f"**{profitable}**, losing: {len(traded_days) - profitable}",
           f"- Win rate: {len(wins) / len(nets) * 100:.0f}%" if nets else "- Win rate: n/a",
           f"- Profit factor: {sum(wins) / -sum(losses):.2f}" if losses else
           "- Profit factor: n/a (no losing trades yet)",
           f"- Biggest drop from a high (max drawdown): {money(max_dd)}",
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
        what = ", ".join(f"{r['instrument']} {r['direction'] or 'no trade'}" for r in days[d])
        out.append(f"| {d} | {what} | {money(day_nets[d])} |")
    out += ["", f"[Every paper trade](paper-journal.md) · [Raw data](trades.csv)", ""]
    return "\n".join(out)


def main(argv=None, now=None):
    argv = sys.argv[1:] if argv is None else argv
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    instruments = [a for a in argv if a in rules.SESSIONS] or list(rules.SESSIONS)

    rows = read_rows()
    recorded = {(r["instrument"], r["session_start"]) for r in rows}
    added = []
    for instrument in instruments:
        try:
            candles = load_from_yahoo(SYMBOLS[instrument], interval="5m", period=LOOKBACK)
        except Exception as error:
            print(f"Could not load {instrument} data: {error}")
            continue
        added += new_sessions(instrument, candles, recorded, now)

    os.makedirs(FOLDER, exist_ok=True)
    rows = sorted(rows + added, key=lambda r: r["session_start"])
    with open(TRADES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    new_trades = sorted((r for r in added if r["signal"] == "yes"),
                        key=lambda r: r["session_start"])
    if new_trades or not os.path.exists(JOURNAL):
        existing = open(JOURNAL).read() if os.path.exists(JOURNAL) else (
            "# Paper trading journal\n\nWritten automatically by paper_trader.py "
            "after each session. Nothing here is a real trade.\n\n---\n\n")
        with open(JOURNAL, "w") as f:
            f.write(existing + "".join(journal_entry(r) for r in new_trades))

    with open(SUMMARY, "w") as f:
        f.write(build_summary(rows, now))

    print(f"Recorded {len(added)} new session(s), {len(new_trades)} with a trade.")
    for r in added:
        print(f"  {r['session_start']} {r['instrument']}: "
              f"{r['direction'] or 'no trade'} {money(float(r['net']))}")
    print(f"Saved {SUMMARY}")


if __name__ == "__main__":
    main()
