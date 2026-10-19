
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
- Key levels = the high and low of the 2 hours before the open (KEY_LEVELS).
- Only the first 60 minutes of a session are scanned for a breakout, and
  at most one trade is taken per session.
- Entry is at the close of the breakout candle. The stop is the other end
  of that candle (low for a long, high for a short).
- For markets in CONFIRM_BREAKOUT, the next candle must also close beyond
  the level. Entry is then at that second candle's close, and the stop is
  the far end of the two candles.
- If a trade is still open when the session ends, it is closed at the last
  candle's close. (Your rules don't say what to do here, so this is a guess.)
- Gold uses the default sell plan 1, 2, 2. In real use the agent chooses.
"""

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data import SYMBOLS, load_candles, load_from_yahoo
from journal import log_trade
from key_levels import build_trade_plan, check_breakout, find_key_levels
from risk import INSTRUMENTS, manage_trade, new_trade, target_price

# ---------------- SETTINGS ----------------
DATA_SOURCE = "yahoo"    # "yahoo" or "csv"
YAHOO_PERIOD = "60d"     # how far back (5-minute data goes back ~60 days)
CSV_FILES = {"nasdaq": "nasdaq.csv", "gold": "gold.csv"}  # used if "csv"
# CSV note: the "time" column must already be in New York time.

JOURNAL_PATH = "backtest-journal.md"   # kept separate from your real journal
ENTRY_WINDOW_MINUTES = 60              # only look for breakouts this long

# Where the key levels come from:
#   "pre_open"          the high and low of the PRE_OPEN_HOURS before the open
#                       (Nasdaq 7:30-9:30 AM, gold 6-8 PM New York in summer)
#   "previous_session"  the high and low of the previous full session (the
#                       original rule, with a 30-minute window)
# On the 60 days to Oct 19, 2026, "pre_open" with a 60-minute window traded
# about 85% of sessions (vs about 60%) and made money in both halves of the
# data, for both markets. Tested in experiments/key_level_test.py.
KEY_LEVELS = "pre_open"
PRE_OPEN_HOURS = 2

# Wait for a second candle to close beyond the level before entering.
# Tested in experiments/gold_variations.py.
CONFIRM_BREAKOUT = {"nasdaq": True, "gold": True}

# "open" is the local time in "zone" (New York if no zone is given). Gold
# opens with Tokyo at 9:00 AM Tokyo time: 8:00 PM New York in summer and
# 7:00 PM in winter, because Japan has no daylight saving time.
SESSIONS = {
    "nasdaq": {"label": "New York", "open": (9, 30), "minutes": 390,
               "name": "Nasdaq (MNQ)"},
    "gold": {"label": "Asia", "open": (9, 0), "zone": "Asia/Tokyo", "minutes": 480,
             "name": "Gold (MGC)"},
}
# Max drawdown, in dollars, across both markets together: if the balance
# (closed trades) falls this far below its highest end-of-day balance,
# trading stops completely, like a failed prop firm account. It never changes
# a trade; it only decides whether more trades are allowed.
MAX_DRAWDOWN = 4000   # raised from $2,500 on 2026-10-19

# Close to the max drawdown: when a closed trade leaves less than NEAR_LIMIT
# dollars of room, stop for the day and take no trade until the next morning's
# Nasdaq open (9:30 AM New York). While the room is still under NEAR_LIMIT,
# trade the small size REDUCED_PLAN (1 contract at each target), and skip a
# trade whose stop would lose more than the room left.
NEAR_LIMIT = 1500   # $1,000 kicked in too late in the 60-day replay (net $4.6k vs $13.5k)
REDUCED_PLAN = [1, 1, 1]

# A session counts as the "previous session" only if it ran at least this
# share of its normal length. This skips holiday half-days (like Labor Day).
FULL_SESSION_SHARE = 0.75
GOLD_SELL_PLAN = [1, 2, 2]   # stand-in for the agent's choice (1 to 3 each)
# ------------------------------------------

NEW_YORK = ZoneInfo("America/New_York")


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
    """Start (New York time) of the session this moment belongs to, or None.

    The open is in config["zone"] (New York if not given). A session that
    opens at 9:00 AM Tokyo time therefore moves by an hour in New York time
    when the US clocks change, and stays at the real Tokyo open.
    """
    zone = ZoneInfo(config.get("zone", "America/New_York"))
    hour, minute = config["open"]
    local = moment.replace(tzinfo=NEW_YORK).astimezone(zone)
    for days_back in (0, 1):
        day = local.date() - timedelta(days=days_back)
        start = (datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
                 .astimezone(NEW_YORK).replace(tzinfo=None))
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


def play_session(instrument, config, start, session, key_high, key_low, size_plan=None):
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
        if CONFIRM_BREAKOUT.get(instrument):
            if index + 1 >= len(session):
                break
            moment, second = session[index + 1]
            if check_breakout(second, key_high, key_low) != direction:
                continue  # the breakout did not hold; keep watching
            index += 1
            entry = round(second.close, 2)
            stop = round(min(candle.low, second.low) if direction == "long"
                         else max(candle.high, second.high), 2)
        if abs(entry - stop) <= 0:
            continue  # no room for a stop; skip this candle

        sell_plan = GOLD_SELL_PLAN if instrument == "gold" else None
        trade = new_trade(instrument, direction, entry, stop, sell_plan)
        if size_plan:   # a smaller size near the max drawdown
            trade["sell_plan"], trade["contracts"] = list(size_plan), sum(size_plan)
        point_value = trade["point_value"]
        contracts = trade["contracts"]
        risk_dollars = round(abs(entry - stop) * point_value * contracts, 2)
        final_target = target_price(trade, len(trade["sell_plan"]))

        events = []        # (time, text)
        exits = []         # (price, contracts) for the average exit price
        fills = []         # one per sale, for the journal
        exit_time = moment

        for later_moment, later in session[index + 1:]:
            actions, trade = manage_trade(trade, later.high, later.low)
            for a in actions:
                if a["action"] == "sell_partial":
                    events.append((later_moment,
                        f"sold {a['contracts']} at Target {a['target']} "
                        f"({a['price']}, ${a['profit']})"))
                    exits.append((a["price"], a["contracts"]))
                    fills.append(_fill(later_moment, f"Target {a['target']}", a))
                elif a["action"] == "move_stop":
                    events.append((later_moment,
                        f"moved stop to {a['reason']} ({a['new_stop']})"))
                elif a["action"] == "exit_target":
                    events.append((later_moment,
                        f"sold the last {a['contracts']} at Target "
                        f"{a['target']} ({a['price']}, ${a['profit']})"))
                    exits.append((a["price"], a["contracts"]))
                    fills.append(_fill(later_moment, f"Target {a['target']}", a))
                elif a["action"] == "exit_stop":
                    events.append((later_moment,
                        f"stop hit, sold {a['contracts']} at {a['price']} "
                        f"(${a['profit']})"))
                    exits.append((a["price"], a["contracts"]))
                    fills.append(_fill(later_moment, "Stop", a))
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
            fills.append({"time": f"{last_moment:%H:%M}", "what": "Session end",
                          "contracts": trade["contracts"], "price": round(last.close, 2),
                          "profit": profit})
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
            "fills": fills,
            "entry_index": index,
            "sell_plan": trade["sell_plan"],
            "contracts": contracts,
            "risk_dollars": risk_dollars,
            "key_high": key_high,
            "key_low": key_low,
        }

    return None  # no breakout: do not force a trade


def _fill(moment, what, action):
    return {"time": f"{moment:%H:%M}", "what": what, "contracts": action["contracts"],
            "price": action["price"], "profit": action["profit"]}


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


def previous_full_session(sessions, starts, i, config):
    """Start of the last full-length session before starts[i], or None.

    Holiday half-days are skipped, and a gap of more than 4 days means there
    is no usable previous session.
    """
    full = FULL_SESSION_SHARE * config["minutes"] / 5
    for j in range(i - 1, -1, -1):
        if (starts[i] - starts[j]).days > 4:
            return None
        if len(sessions[starts[j]]) >= full:
            return starts[j]
    return None


def key_levels_for(sessions, starts, i, config, candles_by_time=None):
    """(high, low) the session starts[i] trades against, or None.

    candles_by_time: [(time, candle), ...] of ALL candles in time order,
    needed for "pre_open" (the pre-open hours are outside the session).
    """
    if KEY_LEVELS == "pre_open":
        start = starts[i]
        since = start - timedelta(hours=PRE_OPEN_HOURS)
        pre = [c for t, c in candles_by_time or [] if since <= t < start]
        if len(pre) < PRE_OPEN_HOURS * 12 / 2:   # at least half the candles
            return None
        return find_key_levels(pre)
    prev = previous_full_session(sessions, starts, i, config)
    if prev is None:
        return None
    return find_key_levels([c for _, c in sessions[prev]])


def timeline(candles):
    """[(time, candle), ...] in time order."""
    return sorted(((parse_time(c.time), c) for c in candles), key=lambda p: p[0])


def trading_day(start):
    """Futures trading days start at 6 PM New York, so an evening session
    (gold at the Tokyo open) belongs to the next day."""
    return (start + timedelta(days=1)).date() if start.hour >= 18 else start.date()


class Account:
    """Tracks the max drawdown across both markets, and the pause and small
    size near it."""

    def __init__(self, max_drawdown=MAX_DRAWDOWN):
        self.max_drawdown = max_drawdown
        self.balance = self.peak_eod = 0.0
        self.day = None
        self.stopped_on = None   # the trading day max drawdown was hit
        self.paused_until = None # no trades before this time (New York)

    def room(self):
        """Dollars left before the max drawdown (today's open gains above the
        end-of-day high are not counted until the day closes)."""
        return min(self.max_drawdown, self.max_drawdown - (self.peak_eod - self.balance))

    def mode(self, start):
        """'normal', 'reduced' (small size), 'paused' or 'stopped' for a
        session starting at start."""
        if not self.can_trade(start):
            return "stopped"
        if self.paused_until and start < self.paused_until:
            return "paused"
        return "reduced" if self.room() < NEAR_LIMIT else "normal"

    def can_trade(self, start):
        day = trading_day(start)
        if day != self.day:      # a new day: yesterday's close may be a new high
            self.peak_eod = max(self.peak_eod, self.balance)
            self.day = day
        return self.stopped_on is None

    def record(self, profit, start=None):
        self.balance += profit
        if self.stopped_on is None and self.balance <= self.peak_eod - self.max_drawdown:
            self.stopped_on = self.day
        elif start is not None and self.room() < NEAR_LIMIT:
            morning = start.date() + timedelta(days=1)
            self.paused_until = datetime(morning.year, morning.month, morning.day, 9, 30)


def run_account(candles_by_instrument, account=None):
    """Replay both markets together, in time order, with the max drawdown.
    Returns (results, account)."""
    account = account or Account()
    plan = []   # (start, instrument, session, key_high, key_low)
    for instrument, candles in candles_by_instrument.items():
        config = SESSIONS[instrument]
        sessions = group_into_sessions(candles, config)
        starts = list(sessions)
        everything = timeline(candles)
        for i in range(1, len(starts)):
            levels = key_levels_for(sessions, starts, i, config, everything)
            if levels is not None:
                plan.append((starts[i], instrument, sessions[starts[i]], *levels))
    results = []
    for start, instrument, session, key_high, key_low in sorted(plan, key=lambda p: p[0]):
        mode = account.mode(start)
        if mode == "stopped":
            break
        if mode == "paused":
            continue
        result = play_session(instrument, SESSIONS[instrument], start, session,
                              key_high, key_low,
                              size_plan=REDUCED_PLAN if mode == "reduced" else None)
        if result is None:
            continue
        if mode == "reduced" and too_risky(result, account.room()):
            continue
        account.record(result["profit"], start)
        results.append(result)
    return results, account


def too_risky(result, room):
    """True when hitting the stop would lose more than the room left."""
    return result["risk_dollars"] >= room


def run_replay(candles, instrument, journal_path=JOURNAL_PATH):
    """Replay every session in the candles. Returns a list of results."""
    config = SESSIONS[instrument]
    sessions = group_into_sessions(candles, config)
    starts = list(sessions)
    everything = timeline(candles)
    results = []

    for i in range(1, len(starts)):
        start = starts[i]
        levels = key_levels_for(sessions, starts, i, config, everything)
        if levels is None:
            continue  # no usable key levels
        key_high, key_low = levels
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

    loaded = {}
    for instrument in instruments:
        try:
            loaded[instrument] = load_for(instrument)
        except Exception:
            pass
    if len(loaded) == len(SESSIONS):
        results, account = run_account(loaded)
        profits = [r["profit"] for r in results]
        print(f"\n===== Both markets as one account, with a ${MAX_DRAWDOWN} max drawdown =====")
        print(f"Trades taken: {len(results)}   Winners: {sum(p > 0 for p in profits)}   "
              f"Total: ${round(sum(profits), 2)}")
        if account.stopped_on:
            print(f"Max drawdown was hit on {account.stopped_on}; trading stopped there.")
        else:
            print("Max drawdown was never hit.")

    print(f"\nEvery trade was written to {JOURNAL_PATH}.")
    print("Reminder: this is a replay on past data, not a prediction.")


if __name__ == "__main__":
    main()
