"""
journal.py - Write each trade into trade-journal.md automatically.

Every entry gets a trade number and a date, and follows the template
from your journal file.
"""

from datetime import datetime

JOURNAL_FILE = "trade-journal.md"


def calc_pnl(direction, entry, exit_price, point_value=1.0, size=1):
    """Profit or loss in dollars.

    point_value: dollars per 1.0 price move per contract (check your broker
    for your contract, e.g. NQ and gold have different values).
    size: number of contracts.
    """
    if direction == "long":
        points = exit_price - entry
    else:
        points = entry - exit_price
    return round(points * point_value * size, 2)


def _next_trade_number(path):
    """Count existing '### Trade #' entries and return the next number."""
    try:
        with open(path) as f:
            return f.read().count("### Trade #") + 1
    except FileNotFoundError:
        return 1


def log_trade(trade, path=JOURNAL_FILE):
    """Append one trade to the journal file.

    'trade' is a dictionary with these keys:
    session, instrument, direction, entry_time, entry_price, stop_loss,
    take_profit, exit_time, exit_price, profit_loss, why, how_it_went,
    what_could_improve
    """
    number = _next_trade_number(path)
    today = trade.get("date") or datetime.now().strftime("%Y-%m-%d")

    entry = f"""
### Trade #{number} | {today}
- **Session:** {trade['session']}
- **Instrument:** {trade['instrument']}
- **Direction:** {trade['direction']}
- **Entry time:** {trade['entry_time']}
- **Entry price:** {trade['entry_price']}
- **Stop loss:** {trade['stop_loss']}
- **Take profit:** {trade['take_profit']}
- **Exit time:** {trade['exit_time']}
- **Exit price:** {trade['exit_price']}
- **Profit / Loss:** ${trade['profit_loss']}
- **Why I took the trade:** {trade['why']}
- **How it went:** {trade['how_it_went']}
- **What could have gone better:** {trade['what_could_improve']}

---
"""
    with open(path, "a") as f:
        f.write(entry)
    return number


if __name__ == "__main__":
    # Sample trade so you can see how it works
    sample = {
        "session": "New York",
        "instrument": "NQ",
        "direction": "long",
        "entry_time": "09:35",
        "entry_price": 30150.0,
        "stop_loss": 30140.0,
        "take_profit": 30180.0,
        "exit_time": "10:05",
        "exit_price": 30180.0,
        "profit_loss": calc_pnl("long", 30150.0, 30180.0, point_value=20),
        "why": "Closed above previous session high after 5-min breakout.",
        "how_it_went": "Hit take profit cleanly.",
        "what_could_improve": "Could have entered a candle earlier.",
    }
    number = log_trade(sample, path="test-journal.md")
    print(f"Logged trade #{number} to test-journal.md")
