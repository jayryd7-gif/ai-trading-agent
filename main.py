
"""
main.py - Replay the strategy on past candles and see how it would have done.

This ties the other files together:
  data.py        loads the candles
  key_levels.py  finds the previous session's high and low, spots breakouts
  risk.py        manages the trade across the 3 targets
  journal.py     writes every trade into a journal file

THIS IS A REPLAY (a "backtest"). It does not place orders or touch any
account. Nothing here is a promise of how real trading would go.

How to run (in a terminal, inside your project folder):
    python3 main.py            # runs Nasdaq and gold
    python3 main.py nasdaq     # Nasdaq only
    python3 main.py gold       # gold only

Assumptions made by this replay (change them in the SETTINGS block):
- Candle times are New York time (Yahoo data from data.py is).
- Key levels = the high and low of the previous session of the same kind.
- Only the first 15 minutes of a session are scanned for a breakout, and
  at most one trade is taken per session.
- Entry is at the close of the breakout candle. The stop is the other end
  of that candle (low for a long, high for a short).
- If a trade is still open when the session ends, it is closed at the last
  candle's close. (Your rules don't say what to do here, so this is a guess.)
- Gold uses the default sell plan 1, 2, 2. In real use the agent chooses.
"""

import sys
from datetime import datetime, timedelta

from data import SYMBOLS, load_candles, load_from_yahoo
from journal import log_trade
from key_levels import build_trade_plan, check_breakout, find_key_levels
from risk import INSTRUMENTS, manage_trade, new_trade, target_price

# ---------------- SETTINGS ----------------
DATA_SOURCE = "yahoo"    # "yahoo" or "csv"
YAHOO_PERIOD = "30d"     # how far back (5-minute data goes back ~60 days)
CSV_FILES = {"nasdaq": "nasdaq.csv", "gold": "gold.csv"}  # used if "csv"
# CSV note: the "time" column must already be in New York time.

JOURNAL_PATH = "backtest-journal.md"   # kept separate from your real journal
ENTRY_WINDOW_MINUTES = 15              # only look for breakouts this long

# Session times are New York time. Asia has no daylight saving, so you may
# need to shift the gold open by an hour when the US clocks change.
SESSIONS = {
    "nasdaq": {"label": "New York", "open": (9, 30), "minutes": 390,
               "name": "Nasdaq (MNQ)"},
    "gold": {"label": "Asia", "open": (19, 0), "minutes": 480,
             "name": "Gold (MGC)"},
}
GOLD_SELL_PLAN = [1, 2, 2]   # stand-in for the agent's choice (1 to 3 each)
# ------------------------------------------


def parse_time(text):
    """Turn 'YYYY-MM-DD HH:MM' into a datetime, with a clear error if not."""
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(
            f"Could not read the time '{text}'. Expected 'YYYY-MM-DD HH:MM' "
            "in New York time."
        )


def session_start(moment, config):
    """Return the start time of the session this moment belongs to, or None."""
    hour, minute = config["open"]
    for days_back in (0, 1):
        day = moment.date() - timedelta(days=days_back)
        start = datetime(day.year, day.month, day.day, hour, minute)
        if start <= moment < start + timedelta(minutes=config["minutes"]):
            return start
    return None


def group_into_sessions(candles, config):
    """Return {session_start: [(time, candle), ...]} in time order."""
    sessions = {}
    for candle in candles:
        moment = parse_time(candle.time)
        start = session_start(moment, config)
        if start is not None:
            sessions.setdefault(start, []).append((moment, candle))
    for start in sessions:
        sessions[start].sort(key=lambda pair: pair[0])
    return dict(sorted(sessions.items()))


def _fmt(moment):
    return moment.strftime("%H:%M")


def play_session(instrument, config, start, session, key_high, key_low):
    """Look for a breakout in this session and play the trade out.

    Returns a result dictionary, or None if no trade was taken.
    """
    window = timedelta(minutes=ENTRY_WINDOW_MINUTES)

    for index, (moment, candle) in enumerate(session):
        if moment - start >= window:
            break
        direction = check_breakout(candle, key_high, key_low)
        if direction is None:
            continue

        plan = build_trade_plan(candle, direction)
        entry, stop = plan["entry"], plan["stop_loss"]
        if abs(entry - stop) <= 0:
            continue  # no room for a stop; skip this candle

        sell_plan = GOLD_SELL_PLAN if instrument == "gold" else None
        trade = new_trade(instrument, direction, entry, stop, sell_plan)
        point_value = trade["point_value"]
        contracts = trade["contracts"]
        risk_dollars = round(abs(entry - stop) * point_value * contracts, 2)
        final_target = target_price(trade, len(trade["sell_plan"]))

        events = []        # (time, text)
        exits = []         # (price, contracts) for the average exit price
        exit_time = moment

        for later_moment, later in session[index + 1:]:
            actions, trade = manage_trade(trade, later.high, later.low)
            for a in actions:
                if a["action"] == "sell_partial":
                    events.append((later_moment,
                        f"sold {a['contracts']} at Target {a['target']} "
                        f"({a['price']}, ${a['profit']})"))
                    exits.append((a["price"], a["contracts"]))
                elif a["action"] == "move_stop":
                    events.append((later_moment,
                        f"moved stop to {a['reason']} ({a['new_stop']})"))
                elif a["action"] == "exit_target":
                    events.append((later_moment,
                        f"sold the last {a['contracts']} at Target "
                        f"{a['target']} ({a['price']}, ${a['profit']})"))
                    exits.append((a["price"], a["contracts"]))
                elif a["action"] == "exit_stop":
                    events.append((later_moment,
                        f"stop hit, sold {a['contracts']} at {a['price']} "
                        f"(${a['profit']})"))
                    exits.append((a["price"], a["contracts"]))
            exit_time = later_moment
            if trade["contracts"] == 0:
                break

        # Still open when the session ended: close at the last close
        if trade["contracts"] > 0:
            last_moment, last = session[-1]
            if direction == "long":
                points = last.close - entry
            else:
                points = entry - last.close
            profit = round(points * point_value * trade["contracts"], 2)
            events.append((last_moment,
                f"session ended, sold {trade['contracts']} at {last.close} "
                f"(${profit})"))
            exits.append((last.close, trade["contracts"]))
            trade["banked"] = round(trade["banked"] + profit, 2)
            trade["contracts"] = 0
            exit_time = last_moment

        total_contracts = sum(c for _, c in exits)
        average_exit = round(sum(p * c for p, c in exits) / total_contracts, 2)

        return {
            "instrument": instrument,
            "config": config,
            "date": start.strftime("%Y-%m-%d"),
            "direction": direction,
            "entry_time": moment,
            "entry": entry,
            "stop": stop,
            "final_target": final_target,
            "exit_time": exit_time,
            "average_exit": average_exit,
            "profit": trade["banked"],
            "events": events,
            "sell_plan": trade["sell_plan"],
            "contracts": contracts,
            "risk_dollars": risk_dollars,
            "key_high": key_high,
            "key_low": key_low,
        }

    return None  # no breakout: do not force a trade


def write_to_journal(result, path):
    """Turn a result into a journal entry."""
    direction = result["direction"]
    level_name = "high" if direction == "long" else "low"
    level = result["key_high"] if direction == "long" else result["key_low"]
    way = "above" if direction == "long" else "below"
    label = result["config"]["label"]

    why = (f"{direction.capitalize()} breakout: the candle closed {way} the "
           f"previous {label} session {level_name} ({level}). Entry "
           f"{result['entry']}, stop {result['stop']}, risk "
           f"${result['risk_dollars']} on {result['contracts']} contracts "
           f"(sell plan {result['sell_plan']}).")
    how = "; ".join(f"{_fmt(t)} {text}" for t, text in result["events"])

    return log_trade({
        "date": result["date"],
        "session": label,
        "instrument": result["config"]["name"],
        "direction": direction.capitalize(),
        "entry_time": _fmt(result["entry_time"]),
        "entry_price": result["entry"],
        "stop_loss": result["stop"],
        "take_profit": result["final_target"],
        "exit_time": _fmt(result["exit_time"]),
        "exit_price": result["average_exit"],
        "profit_loss": result["profit"],
        "why": why,
        "how_it_went": how,
        "what_could_improve": "(Replayed trade. Review this one yourself.)",
    }, path=path)


def run_replay(candles, instrument, journal_path=JOURNAL_PATH):
    """Replay every session in the candles. Returns a list of results."""
    config = SESSIONS[instrument]
    sessions = group_into_sessions(candles, config)
    starts = list(sessions)
    results = []

    for i in range(1, len(starts)):
        previous_start, start = starts[i - 1], starts[i]
        if (start - previous_start).days > 4:
            continue  # too big a gap to count as the "previous" session
        key_high, key_low = find_key_levels(
            [c for _, c in sessions[previous_start]])
        result = play_session(instrument, config, start, sessions[start],
                              key_high, key_low)
        if result is not None:
            write_to_journal(result, journal_path)
            results.append(result)
    return results, len(starts) - 1


def print_summary(instrument, results, sessions_checked):
    config = SESSIONS[instrument]
    print(f"\n===== {config['name']} - {config['label']} session =====")
    print(f"Sessions checked: {sessions_checked}")
    print(f"Trades taken:     {len(results)}  "
          f"(no breakout in the other {sessions_checked - len(results)})")
    if not results:
        return

    profits = [r["profit"] for r in results]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    even = len(profits) - len(wins) - len(losses)
    print(f"Winners / losers / even: {len(wins)} / {len(losses)} / {even}")
    print(f"Total profit or loss:    ${round(sum(profits), 2)}")
    print(f"Best trade:  ${max(profits)}    Worst trade: ${min(profits)}")
    if wins:
        print(f"Average winner: ${round(sum(wins) / len(wins), 2)}")
    if losses:
        print(f"Average loser:  ${round(sum(losses) / len(losses), 2)}")

    print("\nTrade by trade:")
    for r in results:
        print(f"  {r['date']}  {r['direction']:<5}  entry {r['entry']}  "
              f"stop {r['stop']}  result ${r['profit']}")


def load_for(instrument):
    if DATA_SOURCE == "csv":
        return load_candles(CSV_FILES[instrument])
    return load_from_yahoo(SYMBOLS[instrument], interval="5m",
                           period=YAHOO_PERIOD)


def main():
    wanted = [name for name in sys.argv[1:] if name in SESSIONS]
    instruments = wanted or list(SESSIONS)

    for instrument in instruments:
        try:
            candles = load_for(instrument)
        except Exception as error:
            print(f"\nCould not load {instrument} data: {error}")
            continue
        results, checked = run_replay(candles, instrument)
        print_summary(instrument, results, checked)

    print(f"\nEvery trade was written to {JOURNAL_PATH}.")
    print("Reminder: this is a replay on past data, not a prediction.")


if __name__ == "__main__":
    main()
