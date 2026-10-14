"""
risk.py - Scale out and ratchet the stop as a trade moves in your favor.

How it works (all numbers can be changed in the SETTINGS block):

1. The trade starts with its normal stop loss. No take-profit is active yet.
2. A "step" is a favorable price move equal to your initial risk
   (the distance from entry to the starting stop).
3. At step 1: sell partial contracts worth about $50 of profit, and move
   the stop loss to breakeven (the entry price).
4. At step 2: move the stop loss so about $50 of profit is locked in on the
   contracts still open.
5. At every further step: lock in another $50 on the open contracts.
   The stop only ever moves in your favor, never back.
6. The final take-profit only becomes active once the stop loss has moved
   into profit (above your entry on a long, below it on a short).
7. The trade ends when the stop is hit (after moving it) or the take-profit
   is reached. The last contract is never sold early.

Nothing here places orders. It looks at an open trade and returns a list of
actions the agent should take.
"""

import math

# ---------------- SETTINGS ----------------
PARTIAL_DOLLARS = 50.0           # profit to bank when selling a partial
LOCK_DOLLARS = 50.0              # extra profit to lock in per step (from step 2)
STEP_MULTIPLE = 1.0              # 1.0 = one step equals the initial risk
SELL_PARTIAL_EVERY_STEP = False  # False = only sell partials at step 1
MIN_ROOM_STEPS = 0.5             # stop is never placed closer than this many
                                 # steps to the current price
# ------------------------------------------


def new_trade(direction, entry, stop_loss, take_profit, contracts):
    """Create the trade record that manage_trade() keeps updating."""
    return {
        "direction": direction,
        "entry": entry,
        "initial_stop": stop_loss,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "contracts": contracts,   # contracts still open
        "level": 0,               # how many steps price has moved in favor
        "banked": 0.0,            # profit already locked in from partials
    }


def _favorable_move(trade, price):
    """Points moved in your favor (negative if against you)."""
    if trade["direction"] == "long":
        return price - trade["entry"]
    return trade["entry"] - price


def _is_beyond(direction, price, level, above_is_hit):
    if above_is_hit:  # for a long, hit means price is at/below the level
        return price <= level if direction == "long" else price >= level
    return price >= level if direction == "long" else price <= level


def manage_trade(trade, price, point_value):
    """Look at an open trade at the latest price.

    point_value: dollars per 1.0 price move per contract
                 (check with your broker for your micro contract).

    Returns (actions, updated_trade). Each action is a dictionary like:
      {"action": "sell_partial", "contracts": 3, "price": ..., "profit": ...}
      {"action": "move_stop", "new_stop": ...}
      {"action": "exit_stop" or "exit_target", "contracts": ..., "profit": ...}
    An empty list means: do nothing.
    """
    t = dict(trade)
    actions = []
    if t["contracts"] <= 0:
        return actions, t

    is_long = t["direction"] == "long"

    # 1. Stop loss hit?
    if _is_beyond(t["direction"], price, t["stop_loss"], above_is_hit=True):
        profit = round(_favorable_move(t, price) * point_value * t["contracts"], 2)
        actions.append({"action": "exit_stop", "contracts": t["contracts"],
                        "price": price, "profit": profit})
        t["banked"] = round(t["banked"] + profit, 2)
        t["contracts"] = 0
        return actions, t

    # 2. Take-profit reached? Only counts once the stop is in profit.
    target_hit = price >= t["take_profit"] if is_long else price <= t["take_profit"]
    stop_in_profit = t["stop_loss"] > t["entry"] if is_long else t["stop_loss"] < t["entry"]
    if stop_in_profit and target_hit:
        profit = round(_favorable_move(t, price) * point_value * t["contracts"], 2)
        actions.append({"action": "exit_target", "contracts": t["contracts"],
                        "price": price, "profit": profit})
        t["banked"] = round(t["banked"] + profit, 2)
        t["contracts"] = 0
        return actions, t

    # 3. Has price moved another step in our favor?
    step = abs(t["entry"] - t["initial_stop"]) * STEP_MULTIPLE
    move = _favorable_move(t, price)
    reached = int(move // step) if move > 0 else 0

    while t["level"] < reached:
        t["level"] += 1
        level = t["level"]

        # Sell a partial (never the last contract)
        if (level == 1 or SELL_PARTIAL_EVERY_STEP) and t["contracts"] > 1:
            per_contract = move * point_value
            n = min(math.ceil(PARTIAL_DOLLARS / per_contract), t["contracts"] - 1)
            profit = round(per_contract * n, 2)
            t["contracts"] -= n
            t["banked"] = round(t["banked"] + profit, 2)
            actions.append({"action": "sell_partial", "contracts": n,
                            "price": price, "profit": profit})

        # Move the stop
        if level == 1:
            new_stop = t["entry"]  # breakeven
        else:
            locked = LOCK_DOLLARS * (level - 1)
            points = locked / (point_value * t["contracts"])
            new_stop = t["entry"] + points if is_long else t["entry"] - points

        # Keep some room so the stop is not right on top of the price
        room = step * MIN_ROOM_STEPS
        if level > 1:
            if is_long:
                new_stop = min(new_stop, price - room)
            else:
                new_stop = max(new_stop, price + room)

        better = new_stop > t["stop_loss"] if is_long else new_stop < t["stop_loss"]
        if better:
            t["stop_loss"] = round(new_stop, 2)
            actions.append({"action": "move_stop", "new_stop": t["stop_loss"]})

    return actions, t


if __name__ == "__main__":
    # Sample: 5 micro Nasdaq contracts (MNQ), $2 per point
    trade = new_trade("long", entry=30150.0, stop_loss=30140.0,
                      take_profit=30200.0, contracts=5)

    for price in [30155.0, 30160.0, 30170.0, 30180.0, 30172.0]:
        actions, trade = manage_trade(trade, price, point_value=2)
        print(f"\nPrice {price}  (open: {trade['contracts']}, "
              f"stop: {trade['stop_loss']}, banked: ${trade['banked']})")
        if not actions:
            print("  hold")
        for a in actions:
            print("  ->", a)

    print(f"\nFinal result: ${trade['banked']} total profit")
