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

THE ACCOUNT: the bot trades on a Tradeify Growth 50K practice account
(agents/tradeify.py, ACCOUNT below), so each trade is sized to fit that
account's daily loss limit and trailing drawdown, and the summary tracks the
evaluation, the funded account and its payout rules.

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
from risk import INSTRUMENTS
from trade_review import draw, review, tradingview_link
from tradeify import RULES as TRADEIFY, TradeifyAccount, payout_status

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
# Near the max drawdown (less than main.NEAR_LIMIT left) the paper trader
# pauses until the next morning, then trades the small size (main.REDUCED_PLAN).
# Max drawdown: main.MAX_DRAWDOWN ($4,000). Once hit, no more paper trades are
# taken. To start a fresh account after that, set this to the first trading
# day of the new account, like "2026-11-02".
DRAWDOWN_RESET_DAY = None

# The account the bot trades on. "tradeify": a Tradeify Growth 50K practice
# account (agents/tradeify.py) - every trade is sized so its stop cannot break
# the daily loss limit or the trailing drawdown, a $600 day ends trading for
# the day, and evaluations and funded payouts are tracked. "own": the bot's own
# account with main.MAX_DRAWDOWN and the pause near it.
ACCOUNT = "tradeify"

# ------------------------------------------

FIELDS = ["trading_day", "instrument", "session_start", "signal", "direction",
          "entry_time", "entry", "stop", "exit_time", "average_exit", "contracts",
          "gross", "fees", "net", "events", "sell_plan", "key_high", "key_low",
          "fills", "best_move", "worst_move", "lessons", "chart", "size_mode"]
CHART_FOLDER = os.path.join(FOLDER, "charts")
OPEN_TRADES = os.path.join(FOLDER, "open-trades.json")


trading_day = rules.trading_day
SKIPPED = {"stopped": "stopped by max drawdown", "paused": "paused near max drawdown",
           "skipped": "skipped, risk too big for today's limits",
           "day_stopped": "skipped, daily loss limit hit",
           "day_done": "skipped, daily profit cap reached"}
# Why a session was not traded, by account mode.
WHY_NOT = {
    "paused": lambda a: (f"Not taken: paused until {a.paused_until:%Y-%m-%d %H:%M} because "
                         f"less than ${rules.NEAR_LIMIT:,} was left before the max drawdown."),
    "day_stopped": lambda a: (f"Not taken: the ${rules.DAILY_LOSS_LIMIT:,} daily loss limit "
                              "was reached earlier this trading day."),
    "day_done": lambda a: (f"Not taken: this trading day was already up "
                           f"${a.PROFIT_CAP:,}, the daily profit cap that keeps the biggest "
                           "day small for the 35% consistency rule."),
}


def account_from(rows):
    """The account the bot trades on, after the recorded rows: the Tradeify
    Growth 50K practice account (ACCOUNT = "tradeify"), or the bot's own
    account with main.MAX_DRAWDOWN ("own")."""
    account = TradeifyAccount() if ACCOUNT == "tradeify" else rules.Account()
    for r in sorted(rows, key=lambda r: r["session_start"]):
        if DRAWDOWN_RESET_DAY and r["trading_day"] < DRAWDOWN_RESET_DAY:
            continue
        start = datetime.strptime(r["session_start"], "%Y-%m-%d %H:%M")
        account.mode(start)   # moves the account to this session's day
        if r["signal"] != "yes":
            continue
        if ACCOUNT == "tradeify":
            risk = (abs(float(r["entry"]) - float(r["stop"])) * int(r["contracts"])
                    * INSTRUMENTS[r["instrument"]]["point_value"])
            account.record(float(r["net"]), start, worst=risk)
        else:
            account.record(float(r["net"]), start)
    return account


def blank_row(instrument, start, signal, events, levels=("", "")):
    return {"trading_day": trading_day(start).isoformat(), "instrument": instrument,
            "session_start": f"{start:%Y-%m-%d %H:%M}", "signal": signal, "direction": "",
            "entry_time": "", "entry": "", "stop": "", "exit_time": "", "average_exit": "",
            "contracts": 0, "gross": 0.0, "fees": 0.0, "net": 0.0, "events": events,
            "key_high": levels[0], "key_low": levels[1]}


def read_rows():
    try:
        with open(TRADES_CSV, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def new_sessions(instrument, candles, recorded, now, open_now=None, history=()):
    """Rows for sessions whose outcome is known and not in trades.csv yet.
    history: the rows recorded so far. The trades before each session decide
    its size, the pause near the max drawdown, and the stop at it."""
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
        account = account_from([r for r in history if r["session_start"] < key[1]])
        mode = account.mode(start)
        window_over = finished or session[-1][0] >= start + timedelta(
            minutes=rules.ENTRY_WINDOW_MINUTES)
        if mode == "stopped":
            if window_over:
                rows.append(blank_row(instrument, start, "stopped",
                    f"Not taken: the ${rules.MAX_DRAWDOWN:,} max drawdown was hit on "
                    f"{account.stopped_on}.", (round(key_high, 2), round(key_low, 2))))
            continue
        levels_rounded = (round(key_high, 2), round(key_low, 2))
        if mode in WHY_NOT:
            if window_over:
                rows.append(blank_row(instrument, start, mode, WHY_NOT[mode](account),
                                      levels_rounded))
            continue
        result, size = rules.play_with_limits(instrument, start, session, key_high,
                                              key_low, account, mode)
        if size == "skipped":
            rows.append(blank_row(instrument, start, "skipped",
                f"Breakout {result['direction']} at {result['entry_time']:%H:%M}, but even the "
                f"small size risked ${result['risk_dollars']:,.0f} and only "
                f"${account.allowance():,.0f} could be lost today without breaking the "
                "daily loss limit or the drawdown, so it was skipped.", levels_rounded))
            continue
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
                "size_mode": size,
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
    if row.get("size_mode") == "reduced":
        out.append(f"- **Small size:** less than ${rules.NEAR_LIMIT:,} was left before the "
                   f"${rules.MAX_DRAWDOWN:,} max drawdown, so it traded 1 contract per target.")
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


def money(value):
    return f"-${-value:,.0f}" if value < 0 else f"${value:,.0f}"


def tradeify_section(rows):
    """The Tradeify Growth 50K practice account: every evaluation and funded
    account so far, and what is still needed for the next step."""
    r = TRADEIFY
    account = account_from(rows)
    current = account.a
    attempts = account.finish()
    out = ["", f"## Tradeify Growth 50K (practice account the bot trades on)", "",
           f"Rules from Tradeify's help center (Oct 2026): evaluation passes at "
           f"${r['start'] + r['target']:,}; trailing drawdown ${r['drawdown']:,} below the highest "
           f"end-of-day balance, and touching it even with an open trade fails the account; "
           f"daily loss limit ${r['daily_loss_limit']:,} ends the day. Funded: a payout needs "
           f"${r['payout_balance']:,}, {r['payout_days']} days over ${r['payout_day_min']}, and "
           f"the biggest day at most {r['consistency']:.0%} of the profit. The bot sizes every "
           f"trade so its stop cannot break a rule, and stops for the day once up "
           f"${TradeifyAccount.PROFIT_CAP:,}. Check Tradeify's current rules before relying on this.", ""]
    if current is not None:
        cushion = current["balance"] - (current["peak_eod"] - r["drawdown"]
                                        if not (current["phase"] == "Funded"
                                                and current["peak_eod"] >= r["lock_at"])
                                        else r["locked_floor"])
        out.append(f"**Now: {current['phase']}**, balance **{money(current['balance'])}**, "
                   f"{money(cushion)} above the drawdown floor.")
        if current["phase"] == "Evaluation":
            left = r["start"] + r["target"] - current["balance"]
            out.append(f"- To pass: {money(max(0, left))} more profit.")
        else:
            ok, text = payout_status(current)
            out.append(f"- Next payout: {'✅ ready to request' if ok else 'not yet'}: {text}.")
        out.append("")
    out += ["| # | Account | Started | Ended | Trading days | Balance | Result | Payouts | Note |",
            "|---|---|---|---|---|---|---|---|---|"]
    for i, a in enumerate(attempts, 1):
        paid = ", ".join(f"{money(p)} on {d}" for d, p in a["payouts"]) or "–"
        out.append(f"| {i} | {a['phase']} | {a['start'] or '–'} | {a['end'] or '–'} | {a['days']} | "
                   f"{money(a['balance'])} | {a['result']} | {paid} | {a['note']} |")
    return out


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

    out += tradeify_section(rows)

    out += ["", "## Daily results", "", "| Trading day | Sessions | Result after fees |",
            "|---|---|---|"]
    for d in list(days)[::-1][:30]:
        what = ", ".join(f"{r['instrument']} {r['direction'] or SKIPPED.get(r['signal'], 'no trade')}" for r in days[d])
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
    account = account_from(rows)
    if new_trades and account.paused_until and account.stopped_on is None:
        send("Paper trading paused until tomorrow morning",
             f"Only {money(account.room())} is left before the {money(rules.MAX_DRAWDOWN)} max "
             f"drawdown. No trades until {account.paused_until:%a %H:%M} New York, then the "
             "small size (1 contract per target) until the room is back.",
             priority="high", tags="warning")
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
    loaded = {}
    for instrument in instruments:
        try:
            loaded[instrument] = load_from_yahoo(SYMBOLS[instrument], interval="5m",
                                                 period=LOOKBACK)
        except Exception as error:
            print(f"Could not load {instrument} data: {error}")

    # One session at a time, oldest first across both markets, so each one
    # sees the account (size, pause, max drawdown) left by the ones before.
    added, open_now = [], {}
    while True:
        recorded = {(r["instrument"], r["session_start"]) for r in rows + added}
        found, open_now = [], {}
        for instrument, candles in loaded.items():
            found += new_sessions(instrument, candles, recorded, now, open_now,
                                  rows + added)
        if not found:
            break
        added.append(min(found, key=lambda r: r["session_start"]))

    os.makedirs(FOLDER, exist_ok=True)
    rows = sorted(rows + added, key=lambda r: r["session_start"])
    stopped_on = account_from(rows).stopped_on
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
              f"{r['direction'] or SKIPPED.get(r['signal'], 'no trade')} {money(float(r['net']))}")
    print(f"Saved {SUMMARY}")


if __name__ == "__main__":
    main()
