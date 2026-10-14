"""
risk.py - Apply your trade-management rules.

Your rules, in plain English:
- Once a trade is $25 in profit, move the stop loss to breakeven (the entry).
- Take profit at $50, but only by hand if the trade has been open more than
  15 minutes and the take-profit order has not already filled by itself.

Nothing here places orders. It only looks at an open trade and says what
should happen next.
"""

BREAKEVEN_AT = 25.0      # dollars in profit that trigger breakeven
TAKE_PROFIT_AT = 50.0    # dollars in profit to take profit
MIN_MINUTES_OPEN = 15    # wait this long before taking profit by hand


def open_profit(trade, price, point_value=1.0, size=1):
    """Current profit or loss in dollars at the given price."""
    if trade["direction"] == "long":
        points = price - trade["entry"]
    else:
        points = trade["entry"] - price
    return round(points * point_value * size, 2)


def manage_trade(trade, price, minutes_open, point_value=1.0, size=1):
    """Look at an open trade and decide what to do.

    trade: dictionary with keys direction, entry, stop_loss, take_profit
    price: the latest price
    minutes_open: how long the trade has been open

    Returns (action, trade) where action is one of:
      "exit_stop"       - stop loss was hit, get out
      "exit_target"     - take-profit price was hit, get out
      "move_to_breakeven" - stop moved to entry (trade is updated)
      "exit_manual_tp"  - $50 reached after 15+ minutes, take profit by hand
      "hold"            - do nothing yet
    """
    is_long = trade["direction"] == "long"

    # 1. Stop loss hit?
    if (is_long and price <= trade["stop_loss"]) or (
        not is_long and price >= trade["stop_loss"]
    ):
        return "exit_stop", trade

    # 2. Take-profit price hit?
    if (is_long and price >= trade["take_profit"]) or (
        not is_long and price <= trade["take_profit"]
    ):
        return "exit_target", trade

    profit = open_profit(trade, price, point_value, size)

    # 3. $50 reached, trade open 15+ minutes, target has not filled -> take it
    if profit >= TAKE_PROFIT_AT and minutes_open > MIN_MINUTES_OPEN:
        return "exit_manual_tp", trade

    # 4. $25 in profit -> move stop to breakeven (only once)
    if profit >= BREAKEVEN_AT and trade["stop_loss"] != trade["entry"]:
        updated = dict(trade)
        updated["stop_loss"] = trade["entry"]
        return "move_to_breakeven", updated

    return "hold", trade


if __name__ == "__main__":
    # Sample long trade on NQ ($20 per point, 1 contract)
    trade = {"direction": "long", "entry": 30150.0,
             "stop_loss": 30140.0, "take_profit": 30180.0}

    # (price, minutes open) as the trade plays out
    steps = [(30152.0, 2), (30152.0, 5), (30156.0, 8),
             (30153.0, 12), (30157.0, 20), (30139.0, 25)]

    for price, minutes in steps:
        action, trade = manage_trade(trade, price, minutes, point_value=20)
        pnl = open_profit(trade, price, point_value=20)
        print(f"price {price} | {minutes:>2} min | P/L ${pnl:>7} | "
              f"stop {trade['stop_loss']} | -> {action}")
