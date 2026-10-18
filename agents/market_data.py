"""
market_data.py - Pulls real price and volume data and works out the key
facts (previous highs and lows, overnight range, volume) for the brief.

Python does the math here, so the AI reads real numbers instead of guessing.
Data comes from Yahoo Finance, so it can be delayed or occasionally missing.
All times are New York time.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ---------------- SETTINGS ----------------
# "open" is the local time in "zone" (New York if no zone is given). Gold
# follows the Tokyo open: 8:00 PM New York in summer, 7:00 PM in winter.
INSTRUMENTS = {
    "nasdaq": {"symbol": "NQ=F", "name": "Nasdaq 100 futures",
               "label": "New York", "open": (9, 30), "minutes": 390},
    "gold": {"symbol": "GC=F", "name": "Gold futures",
             "label": "Asia", "open": (9, 0), "zone": "Asia/Tokyo", "minutes": 480},
}
HISTORY_SESSIONS = 5      # how many past sessions to look back over
STALE_AFTER_HOURS = 6     # warn if the newest candle is older than this
# ------------------------------------------

NEW_YORK = ZoneInfo("America/New_York")


def load_candles(symbol):
    """Download 5-minute candles (with volume) from Yahoo, in New York time."""
    import yfinance as yf  # imported here so tests can run without it

    history = yf.Ticker(symbol).history(interval="5m", period="14d")
    if history.empty:
        raise ValueError(f"Yahoo returned no data for {symbol}.")
    candles = []
    for stamp, row in history.iterrows():
        local = stamp.tz_convert("America/New_York").tz_localize(None)
        candles.append({
            "time": local.to_pydatetime(),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
        })
    return candles


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


def _group(candles, config):
    sessions = {}
    for c in candles:
        start = session_start(c["time"], config)
        if start is not None:
            sessions.setdefault(start, []).append(c)
    return dict(sorted(sessions.items()))


def _stats(session):
    return {
        "high": max(c["high"] for c in session),
        "low": min(c["low"] for c in session),
        "close": session[-1]["close"],
        "volume": sum(c["volume"] for c in session),
    }


def describe_market(instrument, candles, now):
    """Return a plain-text block of facts about this market (or why not)."""
    config = INSTRUMENTS[instrument]
    name, label = config["name"], config["label"]

    sessions = _group(candles, config)
    finished = [(start, s) for start, s in sessions.items()
                if start + timedelta(minutes=config["minutes"]) <= now]
    if not finished:
        return f"PRICE DATA: not enough finished {label} sessions for {name}."

    prev_start, prev_candles = finished[-1]
    prev_end = prev_start + timedelta(minutes=config["minutes"])
    prev = _stats(prev_candles)

    recent = finished[-HISTORY_SESSIONS:]
    recent_stats = [_stats(s) for _, s in recent]
    week_high = max(s["high"] for s in recent_stats)
    week_low = min(s["low"] for s in recent_stats)

    before = finished[-(HISTORY_SESSIONS + 1):-1]
    volume_line = "Volume comparison: not enough history."
    if before:
        average = sum(_stats(s)["volume"] for _, s in before) / len(before)
        if average > 0:
            volume_line = (f"Volume: the previous session traded "
                           f"{prev['volume'] / average:.2f}x the average of "
                           f"the {len(before)} session(s) before it.")

    latest = candles[-1]
    price = latest["close"]
    if price > prev["high"]:
        position = f"ABOVE the previous session high by {price - prev['high']:.2f}"
    elif price < prev["low"]:
        position = f"BELOW the previous session low by {prev['low'] - price:.2f}"
    else:
        position = (f"INSIDE the previous range ({prev['high'] - price:.2f} "
                    f"below the high, {price - prev['low']:.2f} above the low)")

    since = [c for c in candles if prev_end <= c["time"] <= now]
    if since:
        since_line = (f"Since that session closed: high "
                      f"{max(c['high'] for c in since):.2f}, low "
                      f"{min(c['low'] for c in since):.2f}.")
    else:
        since_line = "Since that session closed: no candles yet."

    stale = ""
    if now - latest["time"] > timedelta(hours=STALE_AFTER_HOURS):
        stale = (f"\nWARNING: the newest candle is from {latest['time']:%Y-%m-%d %H:%M}, "
                 "so this data may be stale or the market may be closed.")

    return (
        f"PRICE DATA ({name}, Yahoo Finance, New York time, may be delayed)\n"
        f"Latest price: {price:.2f} at {latest['time']:%Y-%m-%d %H:%M}\n"
        f"Previous {label} session ({prev_start:%Y-%m-%d %H:%M} to "
        f"{prev_end:%H:%M}): high {prev['high']:.2f}, low {prev['low']:.2f}, "
        f"close {prev['close']:.2f}, volume {prev['volume']:,.0f}\n"
        f"Highest high of the last {len(recent)} {label} sessions: {week_high:.2f}\n"
        f"Lowest low of the last {len(recent)} {label} sessions: {week_low:.2f}\n"
        f"{since_line}\n"
        f"Latest price is {position}.\n"
        f"{volume_line}"
        f"{stale}"
    )


def get_market_facts(instrument, now):
    """Download data and describe it. Never crashes: returns a message instead."""
    try:
        candles = load_candles(INSTRUMENTS[instrument]["symbol"])
        return describe_market(instrument, candles, now)
    except Exception as error:
        return (f"PRICE DATA: unavailable ({error}). Do not guess any price "
                "levels or volume.")
