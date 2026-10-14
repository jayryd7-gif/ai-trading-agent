"""
key_levels.py - first building block of the ai-trading-agent.

What it does (no real trading, no internet, no extra installs):
1. Finds the high and low of the previous session (your key levels).
2. Checks whether a new candle closed above or below those levels (breakout).
3. If so, works out an entry, stop loss, and a 3:1 take-profit.

All prices below are made-up sample data so you can run it right away.
"""

from dataclasses import dataclass


@dataclass
class Candle:
    time: str
    high: float
    low: float
    close: float


RISK_REWARD = 3  # rule 6: 3:1 risk-to-reward


def find_key_levels(session):
    """Return (session_high, session_low) from a list of candles."""
    session_high = max(c.high for c in session)
    session_low = min(c.low for c in session)
    return session_high, session_low


def check_breakout(candle, session_high, session_low):
    """Return 'long', 'short', or None based on where the candle closed."""
    if candle.close > session_high:
        return "long"
    if candle.close < session_low:
        return "short"
    return None


def build_trade_plan(candle, direction):
    """Entry at the close, stop at the breakout candle's opposite extreme,
    target at 3x the risk."""
    entry = candle.close
    if direction == "long":
        stop = candle.low
        risk = entry - stop
        target = entry + RISK_REWARD * risk
    else:
        stop = candle.high
        risk = stop - entry
        target = entry - RISK_REWARD * risk
    return {
        "direction": direction,
        "entry": round(entry, 2),
        "stop_loss": round(stop, 2),
        "take_profit": round(target, 2),
        "risk_per_unit": round(risk, 2),
    }


if __name__ == "__main__":
    # Sample "previous session" candles (fake data)
    previous_session = [
        Candle("00:00", high=100.0, low=98.0, close=99.0),
        Candle("01:00", high=101.5, low=98.5, close=101.0),
        Candle("02:00", high=102.0, low=99.5, close=100.5),
        Candle("03:00", high=101.0, low=97.5, close=98.0),
    ]

    high, low = find_key_levels(previous_session)
    print(f"Key levels -> high: {high}, low: {low}")

    # Sample "new session" candles to test against
    new_candles = [
        Candle("08:00", high=101.5, low=99.0, close=101.0),   # inside range
        Candle("08:05", high=103.5, low=101.8, close=103.0),  # breaks above
    ]

    for candle in new_candles:
        direction = check_breakout(candle, high, low)
        if direction is None:
            print(f"{candle.time}: no breakout, do not force a trade")
        else:
            plan = build_trade_plan(candle, direction)
            print(f"{candle.time}: BREAKOUT {direction.upper()} -> {plan}")
