"""
no_trade_journal.py - Writes a journal entry for sessions with no logged trade.

Run it like this (from the project folder, with PYTHONPATH set to ".")
    python agents/no_trade_journal.py nasdaq
    python agents/no_trade_journal.py gold

This is plain code, not an AI agent, so it costs nothing in API credits.
Every sentence comes from real price data, so nothing is guessed.

After a session ends it checks two things: did your rules give a signal, and
did you log a trade in trade-journal.md? Then it writes one entry to
no-trade-journal.md:

  - No signal: it explains exactly why the rules gave no entry (where each
    candle in the first 15 minutes closed compared with the previous high and
    low, the closest call, whether price broke out later, how the session
    compared with recent ones, and what the morning brief said).
  - Signal, but no trade logged: it shows the signal and what the replay would
    have made, and leaves a line for YOUR reason. It cannot know why you
    stayed out, so it never makes one up.

If you logged a trade for the session, no entry is written.
"""

import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import main as replay                      # the replay engine (main.py)
from market_data import INSTRUMENTS
from post_session_review import (describe_replay, find_brief, journal_entries,
                                 latest_finished_session, to_candles)
from scorer import BIAS_LOG, group_sessions, load_ohlc, read_csv

# ---------------- SETTINGS ----------------
NO_TRADE_JOURNAL = "no-trade-journal.md"
HISTORY_SESSIONS = 5       # recent sessions used to judge how busy this one was
QUIET_BELOW = 0.70         # session range under 70% of recent average = quiet
BUSY_ABOVE = 1.30          # over 130% of recent average = busy
# ------------------------------------------

HEADER = """# No-Trade Journal

One entry for every session where no trade was logged. Entries are written
automatically after each session using real price data. Add your own notes
under "Your notes" in any entry.

---
"""


def event_risk_from_brief(row):
    """Read 'Event risk: High/Medium/Low' from the brief file, or None."""
    path = os.path.join("reports", f"{row['date']}-{row['instrument']}-brief.md")
    try:
        text = open(path).read()
    except OSError:
        return None
    match = re.search(r"Event risk.{0,40}?\b(Low|Medium|High)\b", text, re.S)
    return match.group(1) if match else None


def candle_line(c, key_high, key_low):
    """One line saying where a candle closed compared with the key levels."""
    close = c["close"]
    if close > key_high:
        where = f"closed ABOVE the previous high by {close - key_high:.2f}"
    elif close < key_low:
        where = f"closed BELOW the previous low by {key_low - close:.2f}"
    else:
        where = (f"closed inside the range ({key_high - close:.2f} below the "
                 f"high, {close - key_low:.2f} above the low)")
    return f"  - {c['time']:%H:%M} candle: close {close:.2f}, {where}."


def closest_call(window, key_high, key_low):
    """One sentence about how near the entry window came to a signal."""
    best_high = max(c["high"] for c in window)
    best_low = min(c["low"] for c in window)
    poke_up = best_high - key_high
    poke_down = key_low - best_low
    notes = []
    if poke_up > 0:
        notes.append(f"price traded {poke_up:.2f} above the previous high but "
                     "no candle closed above it")
    if poke_down > 0:
        notes.append(f"price traded {poke_down:.2f} below the previous low but "
                     "no candle closed below it")
    if notes:
        return ("A wick went past a level without a close: " + "; and ".join(notes)
                + ". The rules need a close, so a wick alone is not a signal.")
    gap_high, gap_low = key_high - best_high, best_low - key_low
    if gap_high <= gap_low:
        side, level, gap, extreme = "high", key_high, gap_high, best_high
    else:
        side, level, gap, extreme = "low", key_low, gap_low, best_low
    if gap < 0.005:
        return (f"Price touched the previous {side} ({level:.2f}) exactly but "
                "did not trade beyond it.")
    return (f"Price got within {gap:.2f} of the previous {side} "
            f"(its {'highest' if side == 'high' else 'lowest'} point was "
            f"{extreme:.2f}) but never reached it.")


def after_window(session, start, key_high, key_low):
    """What happened after the entry window ended."""
    cutoff = start + timedelta(minutes=replay.ENTRY_WINDOW_MINUTES)
    for c in session:
        if c["time"] < cutoff:
            continue
        if c["close"] > key_high:
            return (f"A candle first closed above the previous high at "
                    f"{c['time']:%H:%M}, but that was after the "
                    f"{replay.ENTRY_WINDOW_MINUTES}-minute window, so the rules "
                    "did not allow an entry.")
        if c["close"] < key_low:
            return (f"A candle first closed below the previous low at "
                    f"{c['time']:%H:%M}, but that was after the "
                    f"{replay.ENTRY_WINDOW_MINUTES}-minute window, so the rules "
                    "did not allow an entry.")
    return "No candle closed beyond either level for the rest of the session."


def range_context(session, earlier_sessions):
    """Compare this session's range with the recent average."""
    this_range = max(c["high"] for c in session) - min(c["low"] for c in session)
    ranges = [max(c["high"] for c in s) - min(c["low"] for c in s)
              for s in earlier_sessions[-HISTORY_SESSIONS:]]
    first, last = session[0]["open"], session[-1]["close"]
    move = last - first
    pct = move / first * 100
    text = (f"The session range was {this_range:.2f} points")
    if ranges and sum(ranges) > 0:
        ratio = this_range / (sum(ranges) / len(ranges))
        label = ("a quiet session" if ratio < QUIET_BELOW
                 else "a busy session" if ratio > BUSY_ABOVE else "a normal session")
        text += (f", {ratio * 100:.0f}% of the average of the last {len(ranges)} "
                 f"({label})")
    text += f". Open to close it moved {move:+.2f} points ({pct:+.2f}%)."
    return text


def build_entry(instrument, start, session, previous, earlier, replay_result, brief_row):
    config = INSTRUMENTS[instrument]
    key_high = max(c["high"] for c in previous)
    key_low = min(c["low"] for c in previous)
    window_end = start + timedelta(minutes=replay.ENTRY_WINDOW_MINUTES)
    window = [c for c in session if c["time"] < window_end]
    open_time = f"{start:%H:%M}"
    prev_date = f"{previous[0]['time']:%Y-%m-%d}"

    lines = [f"### No-trade session | {start:%Y-%m-%d} | {config['label']}",
             f"- **Instrument:** {config['name']}"]

    if replay_result is None:
        broke = [c for c in window if c["close"] > key_high or c["close"] < key_low]
        if broke and replay.CONFIRM_BREAKOUT.get(instrument):
            why = (f"A candle closed beyond a level at {broke[0]['time']:%H:%M}, but "
                   "the next candle did not also close beyond it, so the breakout "
                   "was not confirmed. The previous high was "
                   f"{key_high:.2f} and the previous low {key_low:.2f}.")
        else:
            why = (f"No 5-minute candle closed above the previous high "
                   f"({key_high:.2f}) or below the previous low ({key_low:.2f}) in the "
                   f"first {replay.ENTRY_WINDOW_MINUTES} minutes after the {open_time} open.")
        lines += [
            "- **What happened:** No signal. The rules gave no entry.",
            f"- **Why:** {why} (Previous {config['label']} session was {prev_date}.)",
            f"- **First {replay.ENTRY_WINDOW_MINUTES} minutes, candle by candle:**",
        ]
        lines += [candle_line(c, key_high, key_low) for c in window]
        lines += [f"- **Closest call:** {closest_call(window, key_high, key_low)}",
                  f"- **After the window:** {after_window(session, start, key_high, key_low)}"]
    else:
        r = replay_result
        lines += [
            "- **What happened:** The rules DID give a signal, but no trade was "
            "logged in your journal.",
            f"- **The signal:** {r['direction'].capitalize()} at {r['entry']} "
            f"({r['entry_time']:%H:%M}) after a candle closed "
            f"{'above the previous high' if r['direction'] == 'long' else 'below the previous low'} "
            f"({key_high:.2f} high, {key_low:.2f} low). Stop {r['stop']}, "
            f"about ${r['risk_dollars']} at risk.",
            "- **If it had been taken (replay, perfect fills):**",
        ]
        for t, text in r["events"]:
            lines.append(f"  - {t:%H:%M} {text}")
        lines.append(f"  - Replay result: ${r['profit']}.")
        lines.append("- **Why no trade:** ⚠️ NOT RECORDED. The software cannot know "
                     "your reason. Write it here: ______")
        lines.append("- **If you did trade:** add it to trade-journal.md with a "
                     "heading like `### Trade #1 | " + f"{start:%Y-%m-%d}` so it is not missed.")

    lines.append(f"- **What the market was showing:** {range_context(session, earlier)}")

    if brief_row:
        risk = event_risk_from_brief(brief_row)
        risk_text = f", event risk {risk}" if risk else ""
        lines.append(f"- **The morning brief said:** {brief_row['bias']} "
                     f"({brief_row['confidence']} confidence){risk_text}.")
    else:
        lines.append("- **The morning brief said:** no brief was written for this session.")

    if replay_result is None:
        lines.append("- **Verdict:** Consistent with your rules. There was no "
                     "setup, so staying out was correct under the rules.")
    else:
        lines.append("- **Verdict:** The rules would have traded. If you skipped it on "
                     "purpose, your reason above is the most useful line in this entry.")
    lines += ["- **Your notes:** ", "", "---", ""]
    return "\n".join(lines)


def main(argv=None, now=None):
    argv = sys.argv[1:] if argv is None else argv
    instrument = argv[0] if argv else "nasdaq"
    if instrument not in INSTRUMENTS:
        raise SystemExit(f"Unknown instrument '{instrument}'. Use: {', '.join(INSTRUMENTS)}")
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    config = INSTRUMENTS[instrument]

    try:
        ohlc = load_ohlc(config["symbol"])
    except Exception as error:
        print(f"Could not load {instrument} data, skipping: {error}")
        return None
    sessions = group_sessions(ohlc, config)
    start = latest_finished_session(sessions, config, now)
    if start is None:
        print("No finished session found yet.")
        return None

    marker = f"### No-trade session | {start:%Y-%m-%d} | {config['label']}"
    existing = open(NO_TRADE_JOURNAL).read() if os.path.exists(NO_TRADE_JOURNAL) else ""
    if marker in existing:
        print(f"Already written: {marker}")
        return None

    if journal_entries(config, start):
        print("A trade was logged for this session, so no no-trade entry is needed.")
        return None

    earlier_starts = [s for s in sessions if s < start]
    if not earlier_starts:
        print("No earlier session to compare with, skipping.")
        return None
    previous = sessions[earlier_starts[-1]]
    earlier = [sessions[s] for s in earlier_starts]

    results, _ = replay.run_replay(to_candles(ohlc), instrument, journal_path=os.devnull)
    replay_result = next((r for r in results if r["date"] == f"{start:%Y-%m-%d}"), None)
    brief_row = find_brief(read_csv(BIAS_LOG), instrument, start)

    entry = build_entry(instrument, start, sessions[start], previous, earlier,
                        replay_result, brief_row)
    with open(NO_TRADE_JOURNAL, "w") as f:
        f.write((existing if existing else HEADER) + "\n" + entry)
    print(f"Wrote an entry to {NO_TRADE_JOURNAL}: {marker}")
    return NO_TRADE_JOURNAL


if __name__ == "__main__":
    main()
