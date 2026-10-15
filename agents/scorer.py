"""
scorer.py - Checks how the briefs' directional leans actually turned out.

This is plain code, not an AI agent, so it costs nothing in API credits.

For every brief in reports/bias-log.csv it finds the trading session the
brief was written for, looks at what price really did in that session, and
decides whether the lean was right. Results go to:
    reports/scores.csv     one row per scored brief
    reports/scorecard.md   a readable summary

How a session is judged (change the numbers in SETTINGS if you disagree):
- The session's move = last close minus first open, as a percent.
- If the move is inside the "flat band" it counts as Flat, otherwise Up/Down.
- Bullish is right on Up and wrong on Down. Bearish is the reverse.
  A Flat session is neither right nor wrong for a directional call.
- Neutral is "Calm" if the session ended Flat, and "Moved" if it did not.

Data comes from Yahoo Finance and can be delayed or missing. A brief whose
session is unfinished, or whose data is missing, stays pending and is
checked again on the next run.
"""

import csv
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from market_data import INSTRUMENTS, session_start

# ---------------- SETTINGS ----------------
REPORT_FOLDER = "reports"
BIAS_LOG = os.path.join(REPORT_FOLDER, "bias-log.csv")
SCORES_CSV = os.path.join(REPORT_FOLDER, "scores.csv")
SCORECARD = os.path.join(REPORT_FOLDER, "scorecard.md")

# A session that moves less than this percent (up or down) counts as Flat.
FLAT_BAND_PCT = {"nasdaq": 0.20, "gold": 0.10}
MIN_CANDLES = 12        # fewer candles than this = data too patchy to judge
MAX_WAIT_HOURS = 80     # a brief is matched to a session starting within this
ENOUGH_CALLS = 30       # below this many directional calls = too few to trust
# ------------------------------------------

SCORE_COLUMNS = ["date", "time_ny", "instrument", "bias", "confidence",
                 "session_start", "outcome", "move_pct", "move_points",
                 "result", "broke_prev_high", "broke_prev_low"]


def load_ohlc(symbol):
    """Download 5-minute candles from Yahoo, in New York time."""
    import yfinance as yf  # imported here so tests can run without it

    history = yf.Ticker(symbol).history(interval="5m", period="30d")
    if history.empty:
        raise ValueError(f"Yahoo returned no data for {symbol}.")
    candles = []
    for stamp, row in history.iterrows():
        local = stamp.tz_convert("America/New_York").tz_localize(None)
        candles.append({
            "time": local.to_pydatetime(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        })
    return candles


def group_sessions(candles, config):
    sessions = {}
    for c in candles:
        start = session_start(c["time"], config)
        if start is not None:
            sessions.setdefault(start, []).append(c)
    for start in sessions:
        sessions[start].sort(key=lambda c: c["time"])
    return dict(sorted(sessions.items()))


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def key_of(row):
    return (row["date"], row["time_ny"], row["instrument"])


def judge(bias, outcome):
    """Turn a lean and an outcome into a result word."""
    if bias == "Neutral":
        return "Calm" if outcome == "Flat" else "Moved"
    if outcome == "Flat":
        return "Flat"
    if (bias == "Bullish" and outcome == "Up") or \
       (bias == "Bearish" and outcome == "Down"):
        return "Right"
    return "Wrong"


def score_brief(brief, sessions, config, now):
    """Return a score row for this brief, or None if it is still pending."""
    brief_time = datetime.strptime(f"{brief['date']} {brief['time_ny']}",
                                   "%Y-%m-%d %H:%M")
    limit = brief_time + timedelta(hours=MAX_WAIT_HOURS)

    target = None
    for start in sessions:
        if brief_time <= start <= limit:
            target = start
            break
    if target is None:
        return None

    session_end = target + timedelta(minutes=config["minutes"])
    if session_end > now:
        return None  # session not finished yet

    candles = sessions[target]
    if len(candles) < MIN_CANDLES:
        return None  # not enough data to judge fairly

    first_open = candles[0]["open"]
    last_close = candles[-1]["close"]
    points = last_close - first_open
    pct = points / first_open * 100

    band = FLAT_BAND_PCT[brief["instrument"]]
    outcome = "Up" if pct > band else "Down" if pct < -band else "Flat"

    broke_high = broke_low = ""
    earlier = [s for s in sessions if s < target]
    if earlier:
        prev = sessions[earlier[-1]]
        prev_high = max(c["high"] for c in prev)
        prev_low = min(c["low"] for c in prev)
        broke_high = "yes" if max(c["high"] for c in candles) > prev_high else "no"
        broke_low = "yes" if min(c["low"] for c in candles) < prev_low else "no"

    return {
        "date": brief["date"], "time_ny": brief["time_ny"],
        "instrument": brief["instrument"], "bias": brief["bias"],
        "confidence": brief["confidence"],
        "session_start": target.strftime("%Y-%m-%d %H:%M"),
        "outcome": outcome, "move_pct": f"{pct:.2f}",
        "move_points": f"{points:.2f}",
        "result": judge(brief["bias"], outcome),
        "broke_prev_high": broke_high, "broke_prev_low": broke_low,
    }


def _rate(rows):
    """Count Right / Wrong / Flat and the hit rate among decisive sessions."""
    right = sum(1 for r in rows if r["result"] == "Right")
    wrong = sum(1 for r in rows if r["result"] == "Wrong")
    flat = sum(1 for r in rows if r["result"] == "Flat")
    decisive = right + wrong
    hit = f"{right / decisive * 100:.0f}%" if decisive else "n/a"
    return right, wrong, flat, hit


def build_scorecard(scores, pending, now):
    directional = [r for r in scores if r["bias"] in ("Bullish", "Bearish")]
    neutral = [r for r in scores if r["bias"] == "Neutral"]
    lines = [f"# Brief scorecard", "",
             f"Updated {now:%Y-%m-%d %H:%M} New York time. "
             f"Scored briefs: {len(scores)}. Waiting to be scored: {pending}.", ""]

    if len(directional) < ENOUGH_CALLS:
        lines += [f"> **Too few directional calls to trust any of this yet.** "
                  f"There are {len(directional)} Bullish or Bearish calls "
                  f"scored. Treat results as noise until there are at least "
                  f"{ENOUGH_CALLS}, and preferably many more.", ""]

    right, wrong, flat, hit = _rate(directional)
    lines += ["## Directional calls (Bullish or Bearish)", "",
              f"- Right: {right}",
              f"- Wrong: {wrong}",
              f"- Session ended flat (neither): {flat}",
              f"- Hit rate when the session was decisive: **{hit}**", ""]

    decisive_sessions = [r for r in scores if r["outcome"] in ("Up", "Down")]
    if decisive_sessions:
        up = sum(1 for r in decisive_sessions if r["outcome"] == "Up")
        lines += [f"For comparison: across all scored sessions, price went up in "
                  f"{up / len(decisive_sessions) * 100:.0f}% of the decisive "
                  f"ones ({up} of {len(decisive_sessions)}). A lean has to "
                  f"beat that, and beat 50%, to be worth anything.", ""]

    lines += ["## By confidence", "", "| Confidence | Right | Wrong | Flat | Hit rate |",
              "|---|---|---|---|---|"]
    for level in ("High", "Medium", "Low"):
        r, w, f, h = _rate([x for x in directional if x["confidence"] == level])
        lines.append(f"| {level} | {r} | {w} | {f} | {h} |")

    lines += ["", "## By instrument", "", "| Instrument | Right | Wrong | Flat | Hit rate |",
              "|---|---|---|---|---|"]
    for name in INSTRUMENTS:
        r, w, f, h = _rate([x for x in directional if x["instrument"] == name])
        lines.append(f"| {name} | {r} | {w} | {f} | {h} |")

    calm = sum(1 for r in neutral if r["result"] == "Calm")
    moved = sum(1 for r in neutral if r["result"] == "Moved")
    lines += ["", "## Neutral calls", "",
              f"- Session stayed calm (flat): {calm}",
              f"- Session moved up or down anyway: {moved}", ""]

    lines += ["## Most recent scored briefs", "",
              "| Brief date | Instrument | Lean | Confidence | Session | Move | Result |",
              "|---|---|---|---|---|---|---|"]
    for r in scores[-15:][::-1]:
        lines.append(f"| {r['date']} | {r['instrument']} | {r['bias']} | "
                     f"{r['confidence']} | {r['session_start']} | "
                     f"{r['outcome']} ({r['move_pct']}%) | {r['result']} |")
    return "\n".join(lines) + "\n"


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    os.makedirs(REPORT_FOLDER, exist_ok=True)

    briefs = [b for b in read_csv(BIAS_LOG)
              if b.get("bias") in ("Bullish", "Bearish", "Neutral")
              and b.get("instrument") in INSTRUMENTS]
    scores = {key_of(r): r for r in read_csv(SCORES_CSV)}
    waiting = [b for b in briefs if key_of(b) not in scores]

    session_cache = {}
    for brief in waiting:
        name = brief["instrument"]
        if name not in session_cache:
            try:
                candles = load_ohlc(INSTRUMENTS[name]["symbol"])
                session_cache[name] = group_sessions(candles, INSTRUMENTS[name])
            except Exception as error:
                print(f"Could not load {name} data: {error}")
                session_cache[name] = None
        sessions = session_cache[name]
        if sessions is None:
            continue
        row = score_brief(brief, sessions, INSTRUMENTS[name], now)
        if row is not None:
            scores[key_of(row)] = row

    ordered = sorted(scores.values(), key=lambda r: (r["date"], r["time_ny"]))
    with open(SCORES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SCORE_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)

    pending = len([b for b in briefs if key_of(b) not in scores])
    with open(SCORECARD, "w") as f:
        f.write(build_scorecard(ordered, pending, now))

    print(f"Briefs: {len(briefs)} | scored: {len(ordered)} | pending: {pending}")
    print(f"Wrote {SCORES_CSV} and {SCORECARD}")


if __name__ == "__main__":
    main()
