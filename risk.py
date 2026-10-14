"""
risk.py - Manage a trade across 4 profit targets, 30 points apart.

Rules (these match trading-rules.md):

- Targets sit 30 points from the entry price, in the trade's direction:
    Long:  entry + 30, +60, +90, +120
    Short: entry - 30, -60, -90, -120
- Every time price touches a target, sell a partial (2 contracts on Nasdaq,
  1 to 3 on gold, chosen by the agent).
- Target 2 hit: move the stop loss to breakeven (the entry price).
- Target 3 hit: move the stop loss to Target 1.
- Target 4 is the take profit: sell everything that is left.
- The trade also ends if the stop loss is touched.
- The stop only ever moves in your favor.
- The last contract is never sold before Target 4.

A target counts as hit when a candle's high (long) or low (short) touches it.
If one candle touches both the stop and a target, the stop is assumed to
have been hit first. If one candle passes several targets, they are applied
in order.

Nothing here places orders. It returns a list of actions for the agent.
"""

# ---------------- SETTINGS ----------------
TARGET_SPACING = 30   # points between targets (same for Nasdaq and gold)
NUMBER_OF_TARGETS = 4

INSTRUMENTS = {
    # point_value = dollars per 1.0 point per contract. Confirm with your broker.
    "nasdaq": {"point_value": 2.0, "min_per_target": 2, "max_per_target": 2},
    "gold": {"point_value": 10.0, "min_per_target": 1, "max_per_target": 3},
}
# ------------------------------------------


def partial_size(instrument, wanted=None):
    """How many contracts to sell at each target.

    Nasdaq is fixed at 2. For gold the agent picks 1 to 3 based on market
    conditions; anything outside that range is pulled back into it.
    """
    rules = INSTRUMENTS[instrument]
    if wanted is None:
        wanted = rules["max_per_target"]
    return max(rules["min_per_target"], min(wanted, rules["max_per_target"]))


def new_trade(direction, entry, stop_loss, contracts, per_target):
    """Create the trade record that manage_trade() keeps updating."""
    return {
        "direction": direction,
        "entry": entry,
        "stop_loss": stop_loss,
        "contracts": contracts,     # contracts still open
        "per_target": per_target,   # contracts sold at each target
        "targets_hit": 0,
        "banked": 0.0,              # profit already taken
    }


def target_price(trade, number):
    """Price of target 1, 2, 3 or 4."""
    distance = TARGET_SPACING * number
    if trade["direction"] == "long":
        return trade["entry"] + distance
    return trade["entry"] - distance


def _profit(trade, exit_price, contracts, point_value):
    if trade["direction"] == "long":
        points = exit_price - trade["entry"]
    else:
        points = trade["entry"] - exit_price
    return round(points * point_value * contracts, 2)


def manage_trade(trade, high, low, point_value):
    """Look at one candle's high and low for an open trade.

    Returns (actions, updated_trade). Each action is a dictionary like:
      {"action": "sell_partial", "target": 1, "contracts": 2, "price": ..., "profit": ...}
      {"action": "move_stop", "new_stop": ..., "reason": ...}
      {"action": "exit_target", "target": 4, "contracts": ..., "price": ..., "profit": ...}
      {"action": "exit_stop", "contracts": ..., "price": ..., "profit": ...}
    An empty list means: do nothing.

    Fills are assumed to happen exactly at the target or stop price. Real
    fills can be worse, especially in fast markets.
    """
    t = dict(trade)
    actions = []
    if t["contracts"] <= 0:
        return actions, t

    is_long = t["direction"] == "long"

    # 1. Stop loss touched? The stop is checked first (worst case).
    stop_touched = low <= t["stop_loss"] if is_long else high >= t["stop_loss"]
    if stop_touched:
        profit = _profit(t, t["stop_loss"], t["contracts"], point_value)
        actions.append({"action": "exit_stop", "contracts": t["contracts"],
                        "price": t["stop_loss"], "profit": profit})
        t["banked"] = round(t["banked"] + profit, 2)
        t["contracts"] = 0
        return actions, t

    # 2. Work through the targets in order
    while t["targets_hit"] < NUMBER_OF_TARGETS:
        number = t["targets_hit"] + 1
        price = target_price(t, number)
        touched = high >= price if is_long else low <= price
        if not touched:
            break
        t["targets_hit"] = number

        if number == NUMBER_OF_TARGETS:
            # Final target = take profit: sell everything left
            profit = _profit(t, price, t["contracts"], point_value)
            actions.append({"action": "exit_target", "target": number,
                            "contracts": t["contracts"], "price": price,
                            "profit": profit})
            t["banked"] = round(t["banked"] + profit, 2)
            t["contracts"] = 0
            return actions, t

        # Sell a partial, but always keep at least one contract
        sell = min(t["per_target"], t["contracts"] - 1)
        if sell > 0:
            profit = _profit(t, price, sell, point_value)
            t["contracts"] -= sell
            t["banked"] = round(t["banked"] + profit, 2)
            actions.append({"action": "sell_partial", "target": number,
                            "contracts": sell, "price": price,
                            "profit": profit})

        # Move the stop
        new_stop = None
        if number == 2:
            new_stop, reason = t["entry"], "breakeven"
        elif number == 3:
            new_stop, reason = target_price(t, 1), "Target 1"
        if new_stop is not None:
            better = new_stop > t["stop_loss"] if is_long else new_stop < t["stop_loss"]
            if better:
                t["stop_loss"] = new_stop
                actions.append({"action": "move_stop", "new_stop": new_stop,
                                "reason": reason})

    return actions, t


if __name__ == "__main__":
    # Sample: 8 micro Nasdaq contracts, long from 30150, stop at 30140
    size = partial_size("nasdaq")
    trade = new_trade("long", entry=30150.0, stop_loss=30140.0,
                      contracts=8, per_target=size)
    point_value = INSTRUMENTS["nasdaq"]["point_value"]

    # (high, low) of each 5-minute candle
    candles = [(30160, 30145), (30182, 30158), (30212, 30175),
               (30241, 30205), (30275, 30230)]

    for number, (high, low) in enumerate(candles, start=1):
        actions, trade = manage_trade(trade, high, low, point_value)
        print(f"\nCandle {number}: high {high}, low {low}  "
              f"(open: {trade['contracts']}, stop: {trade['stop_loss']}, "
              f"banked: ${trade['banked']})")
        if not actions:
            print("  hold")
        for a in actions:
            print("  ->", a)

    print(f"\nFinal result: ${trade['banked']} total profit")
