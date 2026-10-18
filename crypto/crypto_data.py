"""
crypto_data.py - Free 5-minute crypto candles from Coinbase (no API key).

    from crypto_data import load_candles
    candles = load_candles("BTC-USD", days=365)

Returns the same Candle objects as data.py, with times in New York time, so
the futures code (key levels, breakout check, trade manager) works unchanged.

Downloads are saved in crypto/cache/ (not saved to GitHub), so later runs
only fetch the newest candles.
"""

import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from key_levels import Candle

API = "https://api.exchange.coinbase.com/products/{}/candles?granularity=300&start={}&end={}"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
PER_REQUEST = 300          # Coinbase returns at most 300 candles per request
NEW_YORK = ZoneInfo("America/New_York")


def _fetch(product, start, end):
    url = API.format(product, start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     end.strftime("%Y-%m-%dT%H:%M:%SZ"))
    request = urllib.request.Request(url, headers={"User-Agent": "ai-trading-agent"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except Exception:
            time.sleep(1 + attempt * 2)   # rate limit or a hiccup: wait and retry
    raise RuntimeError(f"Coinbase did not answer for {product} {start} to {end}")


def _read_cache(path):
    rows = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows[int(r["ts"])] = r
    return rows


def load_candles(product="BTC-USD", days=365, now=None):
    """5-minute candles for the last `days` days, oldest first."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{product}-5m.csv")
    rows = _read_cache(path)
    now = now or datetime.now(timezone.utc).replace(second=0, microsecond=0)
    begin = now - timedelta(days=days)
    newest = max(rows) if rows else None
    cursor = datetime.fromtimestamp(newest, timezone.utc) if newest and \
        datetime.fromtimestamp(newest, timezone.utc) > begin else begin

    while cursor < now:
        stop = min(cursor + timedelta(minutes=5 * PER_REQUEST), now)
        for ts, low, high, open_, close, volume in _fetch(product, cursor, stop):
            rows[int(ts)] = {"ts": int(ts), "open": open_, "high": high, "low": low,
                             "close": close, "volume": volume}
        cursor = stop
        time.sleep(0.15)                 # stay well under Coinbase's rate limit

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ts", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows[k] for k in sorted(rows))

    first = int(begin.timestamp())
    candles = []
    for ts in sorted(k for k in rows if k >= first):
        r = rows[ts]
        moment = datetime.fromtimestamp(ts, NEW_YORK).replace(tzinfo=None)
        candles.append(Candle(time=moment.strftime("%Y-%m-%d %H:%M"), high=float(r["high"]),
                              low=float(r["low"]), close=float(r["close"])))
    return candles


if __name__ == "__main__":
    product = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD"
    data = load_candles(product, days=int(sys.argv[2]) if len(sys.argv) > 2 else 365)
    print(f"{product}: {len(data)} candles from {data[0].time} to {data[-1].time}")
