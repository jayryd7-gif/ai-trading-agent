
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
# (a session can override it with "window"; only experiments do for now)

# Where the key levels come from:
#   "pre_open"          the high and low of the PRE_OPEN_HOURS before the open
#                       (Nasdaq 7:30-9:30 AM, gold 6-8 PM New York)
#   "previous_session"  the high and low of the previous full session (the
#                       original rule, with a 30-minute window)
# On the 60 days to Oct 19, 2026, "pre_open" with a 60-minute window traded
# about 85% of sessions (vs about 60%) and made money in both halves of the
# data, for both markets. Tested in experiments/key_level_test.py.
KEY_LEVELS = "pre_open"
PRE_OPEN_HOURS = 2

# The buy candle (the second, confirming one) must CLOSE above the previous
# candle's high (below its low for a short), not just poke through with a wick.
ENTRY_CLOSE_BEYOND_PREV = False
# And close strongly: the wick left against the trade (above the close for a
# long) may be at most this many times the candle's body (None = no check).
ENTRY_MAX_WICK = None
# Stop this many points past the two candles' far end, for leeway when price
# comes back to retest the low (0 = at the low exactly).
STOP_BUFFER = {"nasdaq": 0, "gold": 0}
# Which confirmed-breakout candles set the stop: "both" (the far end of the two
# candles) or "second" (only the buy candle, tighter after a huge first candle).
STOP_CANDLES = "both"

# Wait for a second candle to close beyond the level before entering.
# Tested in experiments/gold_variations.py.
CONFIRM_BREAKOUT = {"nasdaq": True, "gold": True}

# "open" is the local time in "zone" (New York if no zone is given). Gold
# opens at 8:00 PM New York all year (chosen 2026-11-02 with
# experiments/time_test.py; it was the Tokyo open, which is 8 PM in summer but
# 7 PM in winter). "early": minutes of early watch before the open (see
# EARLY ENTRIES below; 0 = none). "first_session" keeps the paper trader from
# replaying older sessions at the new time.
SESSIONS = {
    "nasdaq": {"label": "New York", "open": (9, 30), "minutes": 390,
               "name": "Nasdaq (MNQ)", "early": 0},
    "gold": {"label": "Asia", "open": (20, 0), "minutes": 480, "early": 90,
             "name": "Gold (MGC)", "first_session": "2026-11-02 20:00"},
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
# Daily loss limit, like Tradeify's (soft breach): once the trading day (6 PM
# to 5 PM New York, so the evening gold session counts toward the next
# morning's Nasdaq) has lost this much, no more trades that day. A trade whose
# stop would lose more than what is left of today's limit (or of the room
# before the max drawdown) drops to REDUCED_PLAN, or is skipped if even that
# is too big.
DAILY_LOSS_LIMIT = 1250
# For Tradeify's 35% consistency rule: once the trading day has made this
# much, no more trades that day (None = no cap).
DAILY_PROFIT_CAP = None
NEAR_LIMIT = 1500   # $1,000 kicked in too late in the 60-day replay (net $4.6k vs $13.5k)
REDUCED_PLAN = [1, 1, 1]

# A session counts as the "previous session" only if it ran at least this
# share of its normal length. This skips holiday half-days (like Labor Day).
FULL_SESSION_SHARE = 0.75
GOLD_SELL_PLAN = [1, 2, 2]   # stand-in for the agent's choice (1 to 3 each)

# Fakeout re-entry: after a trade is stopped out at its ORIGINAL stop, the
# first later candle in the session that closes back beyond the original entry
# (above it for a long, below for a short) re-enters the same direction, once,
# at the smaller REENTRY_PLAN, with the stop at the far end of that candle.
# It is skipped if its stop could lose more than the day's limits allow.
# Off: on the 60 days to Oct 23, 2026 the re-entries lost money (21 of them,
# 5 winners, -$946; stricter versions did no better). With it off, the
# journal still shows what each re-entry would have done ("reentry_shadow").
REENTRY = False
REENTRY_PLAN = [1, 1, 1]
REENTRY_UNTIL_MINUTES = None   # minutes after the open to stop looking (None: session end)

# EARLY ENTRIES: a session's "early" minutes before its open (gold: 90, so
# from 6:30 PM; Nasdaq: off, it waits for 9:30). Same rule, against the high
# and low of the 2 hours before that watch starts (gold 4:30-6:30 PM, which
# has data from 6 PM), but only on a CLEAR breakout (clear_breakout): both
# candles close in the trade's direction, the entry is no more than half a
# target past the level, and no candle in the 30 minutes before swept the
# level (poked through and closed back). Still one trade per session. Added
# 2026-11-02; on the 30 and 60 days to Oct 30 it helped gold and hurt Nasdaq.
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


def _run_trade(trade, session, index):
    """Manage an open trade over session[index + 1:], then close what is left
    at the session end. Returns (events, exits, fills, exit_time, last_index)."""
    events, exits, fills = [], [], []
    exit_time, last_index = session[index][0], index
    for later_index in range(index + 1, len(session)):
        later_moment, later = session[later_index]
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
        exit_time, last_index = later_moment, later_index
        if trade["contracts"] == 0:
            break

    # Still open when the session ended: close at the last close
    if trade["contracts"] > 0:
        last_moment, last = session[-1]
        points = (last.close - trade["entry"]) if trade["direction"] == "long" \
            else (trade["entry"] - last.close)
        profit = round(points * trade["point_value"] * trade["contracts"], 2)
        events.append((last_moment,
            f"session ended, sold {trade['contracts']} at {last.close} (${profit})"))
        exits.append((last.close, trade["contracts"]))
        fills.append({"time": f"{last_moment:%H:%M}", "what": "Session end",
                      "contracts": trade["contracts"], "price": round(last.close, 2),
                      "profit": profit})
        trade["banked"] = round(trade["banked"] + profit, 2)
        trade["contracts"] = 0
        exit_time, last_index = last_moment, len(session) - 1
    return events, exits, fills, exit_time, last_index, trade


def _reentry(instrument, direction, entry, session, after, max_loss):
    """After a fakeout stop-out: the first later candle that closes back beyond
    the original entry, in the original direction, re-enters at REENTRY_PLAN
    with its stop at the far end of that candle. None if there is none, or if
    its stop could lose more than max_loss."""
    for index in range(after + 1, len(session)):
        moment, candle = session[index]
        if REENTRY_UNTIL_MINUTES is not None and \
                moment - session[0][0] >= timedelta(minutes=REENTRY_UNTIL_MINUTES):
            return None
        beyond = candle.close > entry if direction == "long" else candle.close < entry
        if not beyond:
            continue
        price = round(candle.close, 2)
        stop = round(candle.low if direction == "long" else candle.high, 2)
        if abs(price - stop) <= 0:
            continue
        trade = new_trade(instrument, direction, price, stop)
        trade["sell_plan"], trade["contracts"] = list(REENTRY_PLAN), sum(REENTRY_PLAN)
        risk = abs(price - stop) * trade["point_value"] * trade["contracts"]
        if max_loss is not None and risk >= max_loss:
            return None
        return index, trade, round(risk, 2)
    return None


def upcoming_open(now, config):
    """The next session's open when now is in its early watch, else None."""
    minutes = config.get("early", 0)
    if not minutes:
        return None
    zone = ZoneInfo(config.get("zone", "America/New_York"))
    hour, minute = config["open"]
    local = now.replace(tzinfo=NEW_YORK).astimezone(zone)
    for days_ahead in (0, 1):
        day = local.date() + timedelta(days=days_ahead)
        start = (datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
                 .astimezone(NEW_YORK).replace(tzinfo=None))
        if start - timedelta(minutes=minutes) <= now < start:
            return start
    return None


def early_levels(everything, start, config):
    """(high, low) of the 2 hours before the early watch starts, or None."""
    if not config.get("early", 0):
        return None
    watch = start - timedelta(minutes=config["early"])
    pre = [c for t, c in everything if watch - timedelta(hours=2) <= t < watch]
    if len(pre) < 12:       # at least an hour of candles (gold pauses 5-6 PM)
        return None
    return find_key_levels(pre)


def with_early(everything, start, session, config):
    """The early-watch candles followed by the session's own."""
    if not config.get("early", 0):
        return session
    watch = start - timedelta(minutes=config["early"])
    return [(t, c) for t, c in everything if watch <= t < start] + list(session)


def clear_breakout(instrument, session, index, direction, level):
    """True when the confirmed breakout ending at session[index] is clear:
    both candles close in the trade's direction, the entry is at most half a
    target past the level (no chasing), and no candle in the 30 minutes
    before swept the level (poked through it and closed back)."""
    d = 1 if direction == "long" else -1
    spacing = INSTRUMENTS[instrument]["target_spacing"]
    for i in (index - 1, index):
        c = session[i][1]
        opened = c.open if c.open is not None else session[i - 1][1].close
        if d * (c.close - opened) <= 0:
            return False
    if d * (session[index][1].close - level) > spacing / 2:
        return False
    for _, c in session[max(0, index - 7):index - 1]:
        poke = c.high > level if d == 1 else c.low < level
        if poke and d * (c.close - level) <= 0:
            return False
    return True


def play_session(instrument, config, start, session, key_high, key_low, size_plan=None,
                 max_loss=None, early=None):
    """Look for a breakout in this session and play the trade out, with one
    re-entry after a fakeout stop-out (REENTRY).

    max_loss: the most the session may lose in total (for the re-entry check).
    early: (high, low) for the early watch, or None. session may then start
    with the early-watch candles (with_early).
    Returns a result dictionary, or None if no trade was taken.
    """
    window = timedelta(minutes=config.get("window", ENTRY_WINDOW_MINUTES))

    for index, (moment, candle) in enumerate(session):
        if moment - start >= window:
            break
        is_early = moment < start          # an early-watch candle (see EARLY ENTRIES)
        if is_early and early is None:
            continue
        high, low = early if is_early else (key_high, key_low)
        direction = check_breakout(candle, high, low)
        if direction is None:
            continue

        plan = build_trade_plan(candle, direction)
        entry, stop = plan["entry"], plan["stop_loss"]
        if CONFIRM_BREAKOUT.get(instrument):
            if index + 1 >= len(session):
                break
            moment, second = session[index + 1]
            if is_early and moment >= start:
                continue  # an early breakout must confirm before the open
            if check_breakout(second, high, low) != direction:
                continue  # the breakout did not hold; keep watching
            d = 1 if direction == "long" else -1
            if ENTRY_CLOSE_BEYOND_PREV and \
                    d * (second.close - (candle.high if d == 1 else candle.low)) <= 0:
                continue  # only a wick went past the previous candle
            if ENTRY_MAX_WICK is not None:
                body = abs(second.close - (second.open if second.open is not None else candle.close))
                wick = second.high - second.close if d == 1 else second.close - second.low
                if wick > ENTRY_MAX_WICK * body:
                    continue  # closed well off its best price: a rejection
            index += 1
            entry = round(second.close, 2)
            far = (second.low if direction == "long" else second.high) if STOP_CANDLES == "second" \
                else (min(candle.low, second.low) if direction == "long" else max(candle.high, second.high))
            stop = round(far - d * STOP_BUFFER[instrument], 2)
        if is_early and not clear_breakout(instrument, session, index, direction,
                                           high if direction == "long" else low):
            continue  # not clear enough to go before the open
        if abs(entry - stop) <= 0:
            continue  # no room for a stop; skip this candle

        sell_plan = GOLD_SELL_PLAN if instrument == "gold" else None
        trade = new_trade(instrument, direction, entry, stop, sell_plan)
        if size_plan:   # a smaller size near the max drawdown
            trade["sell_plan"], trade["contracts"] = list(size_plan), sum(size_plan)
        point_value = trade["point_value"]
        contracts = trade["contracts"]
        sell_plan = trade["sell_plan"]
        risk_dollars = round(abs(entry - stop) * point_value * contracts, 2)
        final_target = target_price(trade, len(sell_plan))

        events, exits, fills, exit_time, last_index, trade = _run_trade(trade, session, index)
        profit = trade["banked"]
        worst = risk_dollars

        # A fakeout: stopped out at the ORIGINAL stop (the stop never moved up).
        # If price then closes back beyond the original entry, go again, smaller.
        reentry = shadow = None
        faked_out = bool(fills) and fills[-1]["what"] == "Stop" and fills[-1]["price"] == stop
        if faked_out and not REENTRY:
            found = _reentry(instrument, direction, entry, session, last_index, None)
            if found:
                r_index, r_trade, r_risk = found
                r_stop = r_trade["stop_loss"]
                *_, r_trade = _run_trade(r_trade, session, r_index)
                shadow = {"time": f"{session[r_index][0]:%H:%M}", "entry": r_trade["entry"],
                          "stop": r_stop, "contracts": sum(REENTRY_PLAN),
                          "profit": r_trade["banked"]}
        if faked_out and REENTRY:
            room = None if max_loss is None else max_loss + profit
            found = _reentry(instrument, direction, entry, session, last_index, room)
            if found:
                r_index, r_trade, r_risk = found
                r_moment = session[r_index][0]
                events.append((r_moment,
                    f"fakeout: price closed back beyond the entry, re-entered "
                    f"{direction} {r_trade['contracts']} at {r_trade['entry']}, "
                    f"stop {r_trade['stop_loss']}"))
                fills.append({"time": f"{r_moment:%H:%M}", "what": "Re-entry",
                              "contracts": r_trade["contracts"], "price": r_trade["entry"],
                              "profit": 0.0})
                r_stop = r_trade["stop_loss"]
                r_events, r_exits, r_fills, exit_time, _, r_trade = \
                    _run_trade(r_trade, session, r_index)
                events += r_events
                exits += r_exits
                fills += r_fills
                profit = round(profit + r_trade["banked"], 2)
                worst = max(worst, -trade["banked"] + r_risk)
                reentry = {"time": f"{r_moment:%H:%M}", "entry": r_trade["entry"],
                           "stop": r_stop, "contracts": sum(REENTRY_PLAN),
                           "sell_plan": list(REENTRY_PLAN), "profit": r_trade["banked"],
                           "risk_dollars": r_risk}

        if is_early:
            events.insert(0, (moment, f"early entry before the open: a clear breakout of "
                                      f"the {low:.2f}-{high:.2f} range"))
        sold = sum(c for _, c in exits)
        average_exit = round(sum(p * c for p, c in exits) / sold, 2)

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
            "profit": profit,
            "events": events,
            "fills": fills,
            "entry_index": index,
            "sell_plan": sell_plan,
            "contracts": contracts,
            "risk_dollars": risk_dollars,
            "worst_dollars": round(worst, 2),
            "reentry": reentry,
            "reentry_shadow": shadow,
            "key_high": high,
            "key_low": low,
            "early": is_early,
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
    (gold at 9 PM) belongs to the next day."""
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
        self.day_pnl = 0.0       # closed profit so far this trading day

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
        if self.day_pnl <= -DAILY_LOSS_LIMIT:
            return "day_stopped"
        if DAILY_PROFIT_CAP is not None and self.day_pnl >= DAILY_PROFIT_CAP:
            return "day_done"
        return "reduced" if self.room() < NEAR_LIMIT else "normal"

    def can_trade(self, start):
        day = trading_day(start)
        if day != self.day:      # a new day: yesterday's close may be a new high
            self.peak_eod = max(self.peak_eod, self.balance)
            self.day = day
            self.day_pnl = 0.0
        return self.stopped_on is None

    def allowance(self):
        """The most one trade may lose: what is left of today's loss limit,
        or of the room before the max drawdown, whichever is smaller."""
        return min(self.room(), DAILY_LOSS_LIMIT + self.day_pnl)

    def record(self, profit, start=None):
        self.balance += profit
        self.day_pnl += profit
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
                plan.append((starts[i], instrument,
                             with_early(everything, starts[i], sessions[starts[i]], config),
                             *levels, early_levels(everything, starts[i], config)))
    results = []
    for start, instrument, session, key_high, key_low, early in sorted(plan, key=lambda p: p[0]):
        mode = account.mode(start)
        if mode == "stopped":
            break
        if mode in ("paused", "day_stopped", "day_done"):
            continue
        result, size = play_with_limits(instrument, start, session, key_high, key_low,
                                        account, mode, early)
        if result is None or size == "skipped":
            continue
        result["session"], result["start"] = session, start
        if hasattr(account, "attempts"):     # a prop firm account: open loss matters
            account.record(result["profit"] - contracts_traded(result), start,
                           worst=result["worst_dollars"])
        else:
            account.record(result["profit"], start)
        results.append(result)
    return results, account


def play_with_limits(instrument, start, session, key_high, key_low, account, mode,
                     early=None):
    """Play a session with the size the account allows.
    Returns (result, size_mode): size_mode is "normal", "reduced", or
    "skipped" (result then holds the trade that was not taken)."""
    config = SESSIONS[instrument]
    limit = account.allowance()
    if mode == "normal":
        result = play_session(instrument, config, start, session, key_high, key_low,
                              max_loss=limit, early=early)
        if result is None or not too_risky(result, limit):
            return result, "normal"
    result = play_session(instrument, config, start, session, key_high, key_low,
                          size_plan=REDUCED_PLAN, max_loss=limit, early=early)
    if result is None:
        return None, "reduced"
    if too_risky(result, limit):
        return result, "skipped"
    return result, "reduced"


def contracts_traded(result):
    """Every contract bought or sold short in the session, re-entry included
    (fees are charged per contract)."""
    return result["contracts"] + (result["reentry"]["contracts"] if result.get("reentry") else 0)


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
