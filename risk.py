risk.py - Manage a trade across 3 profit targets, each worth about $60
per contract apart.

Rules (these match trading-rules.md):

- Target spacing is set per market so every target is about $60 per
  contract apart:
    Nasdaq (micro): 30 points  ($2 a point  -> $60)
    Gold (micro):    6 points  ($10 a point -> $60)
- Targets sit that distance from the entry price, in the trade's direction.
  For Nasdaq going long from 30150: 30180, 30210, 30240.
- Contracts sold: 1 at Target 1, 2 at Target 2, and the last 2 at Target 3.
  That is 5 contracts in total.
- Target 3 is the take profit: everything left is sold and the trade ends.
- Target 2 hit: move the stop loss to breakeven (the entry price).
- The trade also ends if the stop loss is touched.
- The stop only ever moves in your favor.
- The last contract is never sold before the final target.

A target counts as hit when a candle's high (long) or low (short) touches it.
If one candle touches both the stop and a target, the stop is assumed to
have been hit first. If one candle passes several targets, they are applied
in order.

Nothing here places orders. It returns a list of actions for the agent.
"""

# ---------------- SETTINGS ----------------
SELL_PLAN = [1, 2, 2]    # contracts sold at target 1, 2, 3 (last = take profit)

# Where the stop goes after a target is hit.
#   "entry" = breakeven, or a number = that target's price.
STOP_RULES = {2: "entry"}

INSTRUMENTS = {
    # point_value = dollars per 1.0 point per contract. Confirm with your broker.
    # target_spacing = points between targets (about $60 per contract).
    "nasdaq": {"point_value": 2.0, "target_spacing": 30},
    "gold": {"point_value": 10.0, "target_spacing": 6},
}
# ------------------------------------------


def new_trade(instrument, direction, entry, stop_loss, contracts=None):
    """Create the trade record that manage_trade() keeps updating.

    contracts defaults to the full plan (1 + 2 + 2 = 5). If you use more,
    the extra contracts ride until the final target.
    """
    rules = INSTRUMENTS[instrument]
    if contracts is None:
        contracts = sum(SELL_PLAN)
    return {
        "instrument": instrument,
        "direction": direction,
        "entry": entry,
        "stop_loss": stop_loss,
        "contracts": contracts,                 # contracts still open
        "spacing": rules["target_spacing"],
        "point_value": rules["point_value"],
        "targets_hit": 0,
        "banked": 0.0,                          # profit already taken
    }


def target_price(trade, number):
    """Price of target 1, 2 or 3."""
    distance = trade["spacing"] * number
    if trade["direction"] == "long":
        return round(trade["entry"] + distance, 2)
    return round(trade["entry"] - distance, 2)


def _profit(trade, exit_price, contracts):
    if trade["direction"] == "long":
        points = exit_price - trade["entry"]
    else:
        points = trade["entry"] - exit_price
    return round(points * trade["point_value"] * contracts, 2)


def manage_trade(trade, high, low):
    """Look at one candle's high and low for an open trade.

    Returns (actions, updated_trade). Each action is a dictionary like:
      {"action": "sell_partial", "target": 1, "contracts": 1, "price": ..., "profit": ...}
      {"action": "move_stop", "new_stop": ..., "reason": ...}
      {"action": "exit_target", "target": 3, "contracts": ..., "price": ..., "profit": ...}
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
    final_target = len(SELL_PLAN)

    # 1. Stop loss touched? The stop is checked first (worst case).
    stop_touched = low <= t["stop_loss"] if is_long else high >= t["stop_loss"]
    if stop_touched:
        profit = _profit(t, t["stop_loss"], t["contracts"])
        actions.append({"action": "exit_stop", "contracts": t["contracts"],
                        "price": t["stop_loss"], "profit": profit})
        t["banked"] = round(t["banked"] + profit, 2)
        t["contracts"] = 0
        return actions, t

    # 2. Work through the targets in order
    while t["targets_hit"] < final_target:
        number = t["targets_hit"] + 1
        price = target_price(t, number)
        touched = high >= price if is_long else low <= price
        if not touched:
            break
        t["targets_hit"] = number

        if number == final_target:
            # Final target = take profit: sell everything left
            profit = _profit(t, price, t["contracts"])
            actions.append({"action": "exit_target", "target": number,
                            "contracts": t["contracts"], "price": price,
                            "profit": profit})
            t["banked"] = round(t["banked"] + profit, 2)
            t["contracts"] = 0
            return actions, t

        # Sell a partial, but always keep at least one contract
        sell = min(SELL_PLAN[number - 1], t["contracts"] - 1)
        if sell > 0:
            profit = _profit(t, price, sell)
            t["contracts"] -= sell
            t["banked"] = round(t["banked"] + profit, 2)
            actions.append({"action": "sell_partial", "target": number,
                            "contracts": sell, "price": price,
                            "profit": profit})

        # Move the stop, if there is a rule for this target
        rule = STOP_RULES.get(number)
        if rule is not None:
            if rule == "entry":
                new_stop, reason = t["entry"], "breakeven"
            else:
                new_stop, reason = target_price(t, rule), f"Target {rule}"
            better = new_stop > t["stop_loss"] if is_long else new_stop < t["stop_loss"]
            if better:
                t["stop_loss"] = new_stop
                actions.append({"action": "move_stop", "new_stop": new_stop,
                                "reason": reason})

    return actions, t


def show_run(title, trade, candles):
    """Print what happens as a list of (high, low) candles plays out."""
    print(f"\n=== {title}")
    for number, (high, low) in enumerate(candles, start=1):
        actions, trade = manage_trade(trade, high, low)
        print(f"Candle {number}: high {high}, low {low}  "
              f"(open: {trade['contracts']}, stop: {trade['stop_loss']}, "
              f"banked: ${trade['banked']})")
        if not actions:
            print("  hold")
        for a in actions:
            print("  ->", a)
    print(f"Final result: ${trade['banked']} total profit")


if __name__ == "__main__":
    # Nasdaq: long from 30150, stop at 30140
    show_run("Nasdaq long", new_trade("nasdaq", "long", 30150.0, 30140.0),
             [(30160, 30145), (30182, 30158), (30212, 30175), (30245, 30200)])

    # Gold: long from 4000, stop at 3996 (same $ spacing as Nasdaq)
    show_run("Gold long", new_trade("gold", "long", 4000.0, 3996.0),
             [(4002, 3999), (4006.5, 4001), (4012.5, 4005), (4019, 4010)])
