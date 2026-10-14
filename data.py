"""
data.py - Load price candles from a CSV file exported from TradingView.

TradingView's chart export has columns like:
    time,open,high,low,close,Volume
The "time" column can be a unix timestamp (e.g. 1760457900) or readable
text (e.g. 2026-10-14T08:05:00Z). This loader handles both.
"""

import csv
from datetime import datetime, timezone

from key_levels import Candle


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


if __name__ == "__main__":
    candles = load_candles("sample_data.csv")
    print(f"Loaded {len(candles)} candles")
    print("First:", candles[0])
    print("Last: ", candles[-1])
