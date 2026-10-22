# Trading Rules

Follow these rules in order. Analyze the market and its moves, show your work, and explain the thought process behind every move.

## Sessions
- **Nasdaq (New York session):** opens at 9:30 AM New York time.
- **Gold (Asia session):** opens with Tokyo at 9:00 AM Tokyo time. That is 8:00 PM New York time while US daylight saving time is on (March to early November) and 7:00 PM the rest of the year, because Japan does not change its clocks.
- Be active and ready 15-30 minutes before the open.
- Only look for breakouts in the first 60 minutes after the open.
- Take at most one trade per session.

## Entry rules
1. Mark the high and low of the **2 hours before the open**. These are your key levels.
   - Nasdaq: 7:30-9:30 AM New York.
   - Gold: 7:00-9:00 AM Tokyo (6:00-8:00 PM New York in summer, 5:00-7:00 PM in winter).
   - Changed on 2026-10-19 from "the previous session's high and low, first 30 minutes".
     On the 60 days before that, the new levels traded about 85% of sessions
     instead of about 60%, and made more in both halves of the data for both
     markets (see experiments/key_level_test.py). To go back, set
     `KEY_LEVELS = "previous_session"` and `ENTRY_WINDOW_MINUTES = 30` in main.py.
2. Wait for a breakout.
3. Enter when a 5-minute candle closes above the previous high (long) or below the previous low (short).
   - Then wait for the next 5-minute candle to also close beyond the level. Enter at that second candle's close. If it closes back inside, there is no trade yet; keep watching for another breakout in the window.
4. Initial stop loss: the other end of the breakout candle (its low for a long, its high for a short). With the confirming candle, use the far end of the two candles.
5. If the market is choppy and not volatile, do not force a trade.

## Trade management: 3 targets

Each target is about $60 per contract from the one before it.

### Target spacing
- **Nasdaq (micro):** 30 points apart
- **Gold (micro):** 6 points apart
- **Long:** Target 1 = entry + 1 spacing, Target 2 = entry + 2 spacings, Target 3 = entry + 3 spacings
- **Short:** the same distances below the entry

### Contracts to sell
- **Nasdaq:** always 5 contracts. Sell 1 at Target 1, 2 at Target 2, and the last 2 at Target 3.
- **Gold:** before entering, choose 1 to 3 contracts to sell at each target, based on market conditions. Explain the choice in the journal. The total number of contracts is the sum of the three numbers.

### What to do at each target
1. **Target 1 is hit:** sell the planned contracts. Leave the stop loss where it is.
2. **Target 2 is hit:** sell the planned contracts and move the stop loss to **Target 1**.
3. **Target 3 is hit:** sell everything that is left. This is the take profit, and the trade is finished.

### Other rules
- The trade also ends if the stop loss is hit. Sell all remaining contracts.
- The stop loss only ever moves in the trade's favor, never back.
- Never sell the last contract before Target 3.
- A target counts as hit when price touches the level, not only when a candle closes there.
- If price passes several targets in one candle, apply each one in order.
- If one candle touches both the stop loss and a target, assume the stop loss was hit first.

## Account rules: Tradeify Growth 50K

The bot trades on a Tradeify Growth 50K practice account (since 2026-10-21),
using Tradeify's rules as written in its help center in October 2026:

- **Evaluation:** pass at $53,000 (+$3,000). No consistency rule.
- **Trailing drawdown:** $2,000 below the highest end-of-day balance. Touching
  it at any moment, open trades included, fails the account. On the funded
  account it locks at $50,100 once the end-of-day balance reaches $52,100.
- **Daily loss limit:** $1,250. After that, no more trades that trading day
  (6 PM to 5 PM New York, so the evening gold session counts toward the next
  morning's Nasdaq session).
- **Every trade is sized to fit:** if hitting the stop could break the daily
  loss limit or the drawdown (with $100 to spare), trade 1 contract per target
  instead; if even that could, skip the trade.
- **Daily profit cap:** once the trading day is up $600, no more trades that
  day. This keeps the biggest day small for the funded account's 35%
  consistency rule.
- **Funded payouts:** balance at least $53,000, 5 trading days over $150
  profit, and the biggest day at most 35% of the profit since the last payout.
  Max payout $1,500, then $2,000, $2,500, $3,000.
- **Always:** flat by 4:45 PM New York, at most 40 micros, no hedging, at
  least one trade a week.

The earlier rule (a $4,000 max drawdown with a pause near it) is still in the
code: set `ACCOUNT = "own"` in agents/paper_trader.py to use it again.

## Choosing gold contract sizes

Before entering a gold trade, read the market and pick one of these four sell plans. The three numbers are the contracts sold at Target 1, Target 2, and Target 3. Write which plan you chose, and why, in the trade journal.

| Market condition | What it looks like | Sell plan | Contracts | If every target is reached |
|---|---|---|---|---|
| **Strong trend** | The breakout candle is large and closes near its high (long) or low (short). Price moves away from the key level with little pullback. | 1, 1, 3 | 5 | $720 |
| **Normal** | A clean breakout, but nothing exceptional. | 1, 2, 2 | 5 | $660 |
| **Weak or slowing** | The breakout candle is small, has long wicks, or price keeps drifting back toward the key level. | 3, 2, 1 | 6 | $600 |
| **Uncertain** | A major news release is within 30 minutes, or conditions are unusually thin or jumpy. | 1, 1, 1 | 3 | $360 |

### Guidelines
- In a strong trend, keep more contracts for Target 3, because each contract earns the most there ($180 versus $60 at Target 1).
- In a weak market, take profit earlier. Selling 3 contracts at Target 1 locks in $180 right away.
- When conditions are uncertain, trade the smallest size.
- If the market is choppy and not volatile, do not force a trade at all. That rule still comes first.
- Never sell more than 3 contracts at one target, and never trade more than 9 contracts in total.
- Choose the plan before entering. Do not change it once the trade is open.

## Explain and journal
- Before each trade, explain why you are about to take it.
- After each trade, explain how it went and what could have gone better.
- Keep a trade journal: entry time, exit time, profit or loss, what you traded, and why.
- Explain each action (sells and stop moves) in the journal.
