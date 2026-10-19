"""
data.py - Load price candles from two places:

1. load_candles(path)          -> a CSV file exported from TradingView
2. load_from_yahoo(symbol,...) -> free Yahoo Finance data (good for practice)

Both return a list of Candle objects, so the rest of the project does not
care where the data came from.

Setup for Yahoo data (one time, in a terminal):
    pip install yfinance
"""

import csv
from datetime import datetime, timezone

from key_levels import Candle

# Yahoo Finance symbols for what you trade
SYMBOLS = {
    "nasdaq": "NQ=F",  # Nasdaq 100 futures
    "gold": "GC=F",    # Gold futures
}


# ---------- Option 1: TradingView CSV ----------

def _clean_time(raw):
    """Turn a unix timestamp into readable text; leave other text as is."""
    raw = raw.strip()
    if raw.isdigit():
        moment = datetime.fromtimestamp(int(raw), tz=timezone.utc)
        return moment.strftime("%Y-%m-%d %H:%M")
    return raw


def load_candles(path):
    """Read a TradingView CSV and return a list of Candle objects."""
    candles = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        # Make column names case-insensitive ("High" and "high" both work)
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        for row in reader:
            candles.append(
                Candle(
                    time=_clean_time(row["time"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    return candles


# ---------- Option 2: Yahoo Finance ----------

def load_from_yahoo(symbol, interval="5m", period="5d"):
    """Download recent candles from Yahoo Finance.

    symbol:   e.g. "NQ=F" or "GC=F" (see SYMBOLS above)
    interval: candle size, e.g. "5m" for 5-minute candles
    period:   how far back, e.g. "5d" for 5 days (5-minute data only goes
              back about 60 days on Yahoo)

    Times are shown in New York time.
    """
    import yfinance as yf  # imported here so the CSV option works without it

    history = yf.Ticker(symbol).history(interval=interval, period=period)
    if history.empty:
        raise ValueError(
            f"Yahoo returned no data for {symbol}. "
            "Check the symbol, your internet, or try a shorter period."
        )

    candles = []
    for timestamp, row in history.iterrows():
        local_time = timestamp.tz_convert("America/New_York")
        candles.append(
            Candle(
                time=local_time.strftime("%Y-%m-%d %H:%M"),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                open=float(row["Open"]),
            )
        )
    return candles


if __name__ == "__main__":
    # Pick ONE of these to try. Remove the "#" in front of the one you want.

    # candles = load_candles("sample_data.csv")
    candles = load_from_yahoo(SYMBOLS["nasdaq"])

    print(f"Loaded {len(candles)} candles")
    print("First:", candles[0])
    print("Last: ", candles[-1])
