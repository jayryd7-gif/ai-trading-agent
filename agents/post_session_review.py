"""
post_session_review.py - Agent #2: reviews a trading session after it ends.

Run it like this (from the project folder, with PYTHONPATH set to ".")
    python agents/post_session_review.py nasdaq
    python agents/post_session_review.py gold

For the most recent finished session it gathers:
  - what price did (computed by software, not guessed)
  - the morning brief and whether its lean held up
  - what your rules would have done (a replay using main.py)
  - any trades you logged in trade-journal.md for that session
  - your trading rules
Then it asks the AI to write a short, honest review: what went well, what to
improve, and what to watch next.

It only READS and WRITES. It cannot trade, and it never edits your journal.
Reviews are saved in reports/reviews/. Each session is reviewed once.
"""

import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import anthropic

import main as replay                      # the replay engine (main.py)
from key_levels import Candle
from market_data import INSTRUMENTS
from research_tools import log_cost
from scorer import (BIAS_LOG, MAX_WAIT_HOURS, group_sessions, load_ohlc,
                    read_csv, score_brief)

# ---------------- SETTINGS ----------------
MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 2000
REVIEW_FOLDER = os.path.join("reports", "reviews")
JOURNAL = "trade-journal.md"
RULES = "trading-rules.md"
BRIEF_CHARS = 3500        # how much of the brief to show the reviewer
# ------------------------------------------

JOURNAL_ENTRY = re.compile(r"^### Trade #(\d+) \| (\d{4}-\d{2}-\d{2})[ \t]*$", re.M)

PROMPT = """You are a post-session reviewer for a beginner day trader who is
learning. Be direct, kind, and specific. The trader trades micro Nasdaq
futures in the New York session and micro gold futures in the Asia session.

Review this session: {name}, {label} session starting {start}.

FACTS COMPUTED BY SOFTWARE (trust these numbers):
{facts}

THE BRIEF written before the session by another AI agent:
{brief}

WHAT THE TRADER'S RULES WOULD HAVE DONE (a software replay. It assumes
perfect fills at target and stop prices, takes at most one trade in the first
{window} minutes{confirm}, and closes anything still open when the session ends):
{replay}

THE TRADER'S ACTUAL JOURNAL ENTRIES FOR THIS SESSION:
{journal}

THE TRADER'S RULES:
{rules}

Write a review of under 450 words with these sections:
1. What the session did
2. Did the brief help? (its lean versus what happened; what it got right or missed)
3. Rules replay versus reality (only compare to real trades if journal entries exist)
4. Your trades (only if journal entries exist: did each one follow the rules? entry, stop, targets, sizing)
5. What went well
6. What to improve (at most 3, each tied to a specific rule or number above)
7. One thing to watch next session

Rules for you:
- Use only the information above. Never invent prices, trades, or news.
- If there are no journal entries, say plainly that no trades were logged, and
  skip section 4. Do not assume the trader took the replay trade.
- Do not tell the trader to buy or sell. Do not predict the next session.
- One session is a tiny sample. Do not draw big conclusions from it.
- Use plain language and short sentences.
"""


def to_candles(ohlc):
    """Convert the scorer's candle dictionaries into main.py's Candle objects."""
    return [Candle(time=c["time"].strftime("%Y-%m-%d %H:%M"), high=c["high"],
                   low=c["low"], close=c["close"]) for c in ohlc]


def latest_finished_session(sessions, config, now):
    finished = [s for s in sessions
                if s + timedelta(minutes=config["minutes"]) <= now]
    return finished[-1] if finished else None


def find_brief(rows, instrument, start):
    """The latest brief written for this session (same matching as the scorer)."""
    best = None
    for row in rows:
        if row.get("instrument") != instrument:
            continue
        try:
            when = datetime.strptime(f"{row['date']} {row['time_ny']}", "%Y-%m-%d %H:%M")
        except (ValueError, KeyError):
            continue
        if when <= start <= when + timedelta(hours=MAX_WAIT_HOURS):
            if best is None or when > best[0]:
                best = (when, row)
    return best[1] if best else None


def read_brief_text(row):
    path = os.path.join("reports", f"{row['date']}-{row['instrument']}-brief.md")
    try:
        text = open(path).read()
    except OSError:
        return "(The brief file could not be found.)"
    return text[:BRIEF_CHARS] + ("\n(brief shortened)" if len(text) > BRIEF_CHARS else "")


def session_facts(candles, previous):
    """Plain-text facts about what price did in the session."""
    first_open, last_close = candles[0]["open"], candles[-1]["close"]
    high = max(candles, key=lambda c: c["high"])
    low = min(candles, key=lambda c: c["low"])
    points = last_close - first_open
    lines = [
        f"Open {first_open:.2f}, close {last_close:.2f}: moved {points:+.2f} points "
        f"({points / first_open * 100:+.2f}%).",
        f"Session high {high['high']:.2f} at {high['time']:%H:%M}, "
        f"low {low['low']:.2f} at {low['time']:%H:%M} "
        f"(range {high['high'] - low['low']:.2f} points).",
    ]
    if previous:
        prev_high = max(c["high"] for c in previous)
        prev_low = min(c["low"] for c in previous)
        lines.append(f"Previous session high {prev_high:.2f}, low {prev_low:.2f}.")
        for label, level, hit, side in (
                ("high", prev_high, [c for c in candles if c["high"] > prev_high], "above"),
                ("low", prev_low, [c for c in candles if c["low"] < prev_low], "below")):
            if hit:
                lines.append(f"Price traded {side} the previous {label} "
                             f"({level:.2f}), first at {hit[0]['time']:%H:%M}.")
            else:
                lines.append(f"Price never traded {side} the previous {label} ({level:.2f}).")
    return "\n".join(lines)


def describe_replay(result, instrument):
    if result is None:
        return ("The rules would NOT have taken a trade: no candle closed above "
                f"the previous high or below the previous low in the first "
                f"{replay.ENTRY_WINDOW_MINUTES} minutes"
                + (", or the next candle did not confirm the breakout."
                   if replay.CONFIRM_BREAKOUT.get(instrument) else "."))
    lines = [
        f"{result['direction'].capitalize()} at {result['entry']} "
        f"({result['entry_time']:%H:%M}), stop {result['stop']}, "
        f"final target {result['final_target']}.",
        f"Sell plan {result['sell_plan']} on {result['contracts']} contracts; "
        f"dollars at risk about ${result['risk_dollars']}.",
    ]
    lines += [f"{t:%H:%M} {text}" for t, text in result["events"]]
    lines.append(f"Replay result: ${result['profit']}.")
    return "\n".join(lines)


def journal_entries(config, start):
    """Journal entries that belong to this session (real entries only)."""
    try:
        text = open(JOURNAL).read()
    except OSError:
        return []
    matches = list(JOURNAL_ENTRY.finditer(text))
    days = {start.date()}
    if config["label"] == "Asia":
        days.add(start.date() + timedelta(days=1))   # trades after midnight
    found = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end].strip()
        block = re.sub(r"\n---\s*$", "", block).strip()
        if datetime.strptime(m.group(2), "%Y-%m-%d").date() not in days:
            continue
        session_line = re.search(r"^- \*\*Session:\*\*(.*)$", block, re.M)
        if session_line and config["label"].lower() not in session_line.group(1).lower():
            continue
        found.append(block)
    return found


def build_review(client, instrument, start, candles, previous, brief_row,
                 lean_result, replay_result, journal, rules):
    config = INSTRUMENTS[instrument]
    if brief_row:
        brief = (f"Lean: {brief_row['bias']} ({brief_row['confidence']} confidence). "
                 f"Outcome check: {lean_result or 'not scored'}.\n\n"
                 + read_brief_text(brief_row))
    else:
        brief = "No brief was written for this session."
    prompt = PROMPT.format(
        name=config["name"], label=config["label"], start=f"{start:%Y-%m-%d %H:%M}",
        facts=session_facts(candles, previous), brief=brief,
        replay=describe_replay(replay_result, instrument),
        window=replay.ENTRY_WINDOW_MINUTES,
        confirm=(", waits for a second candle to confirm the breakout"
                 if replay.CONFIRM_BREAKOUT.get(instrument) else ""),
        journal=("\n\n".join(journal) if journal
                 else "No trades were logged for this session."),
        rules=rules)
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text, response.usage.input_tokens, response.usage.output_tokens, prompt


def main(argv=None, now=None):
    argv = sys.argv[1:] if argv is None else argv
    instrument = argv[0] if argv else "nasdaq"
    force = "--force" in argv
    if instrument not in INSTRUMENTS:
        raise SystemExit(f"Unknown instrument '{instrument}'. Use: {', '.join(INSTRUMENTS)}")
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    config = INSTRUMENTS[instrument]

    try:
        ohlc = load_ohlc(config["symbol"])
    except Exception as error:
        print(f"Could not load {instrument} data, skipping this review: {error}")
        return None
    sessions = group_sessions(ohlc, config)
    start = latest_finished_session(sessions, config, now)
    if start is None:
        print("No finished session found yet, nothing to review.")
        return None

    path = os.path.join(REVIEW_FOLDER, f"{start:%Y-%m-%d}-{instrument}-review.md")
    if os.path.exists(path) and not force:
        print(f"Already reviewed: {path}")
        return None

    earlier = [s for s in sessions if s < start]
    previous = sessions[earlier[-1]] if earlier else None

    brief_row = find_brief(read_csv(BIAS_LOG), instrument, start)
    lean_result = None
    if brief_row:
        scored = score_brief(brief_row, sessions, config, now)
        if scored:
            lean_result = (f"{scored['result']} (the session moved "
                           f"{scored['move_pct']}%, counted as {scored['outcome']})")

    results, _ = replay.run_replay(to_candles(ohlc), instrument, journal_path=os.devnull)
    replay_result = next((r for r in results if r["date"] == f"{start:%Y-%m-%d}"), None)

    try:
        rules = open(RULES).read()
    except OSError:
        rules = "(trading-rules.md not found)"

    client = anthropic.Anthropic()
    text, tokens_in, tokens_out, _ = build_review(
        client, instrument, start, sessions[start], previous, brief_row,
        lean_result, replay_result, journal_entries(config, start), rules)
    if not text:
        raise SystemExit("The model returned no text, so no review was saved.")

    os.makedirs(REVIEW_FOLDER, exist_ok=True)
    with open(path, "w") as f:
        f.write(f"# {config['name']} review - {config['label']} session {start:%Y-%m-%d}\n\n")
        f.write(f"*Written {now:%Y-%m-%d %H:%M} New York time by an AI reviewer. "
                "It can be wrong. One session is a tiny sample.*\n\n")
        f.write("## Facts used\n\n```\n" + session_facts(sessions[start], previous) + "\n```\n\n")
        f.write(text + "\n")
    print(f"Saved {path}")
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    print(f"Estimated cost: ${log_cost(f'review-{instrument}', tokens_in, tokens_out, 0):.2f}")
    return path


if __name__ == "__main__":
    main()
