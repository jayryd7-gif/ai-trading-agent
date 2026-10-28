# Paper trading summary

*Updated 2026-10-28 10:56 New York time. Paper results from real 5-minute candles with perfect fills at target and stop prices, after $1.00 per contract in fees. Real fills can be worse.*

## At a glance

- Total after fees: **-$50** over 11 trades (15 sessions watched)
- Trading days with a trade: **8**, profitable: **3**, losing: 5
- Win rate: 45%
- Profit factor: 0.98
- Biggest drop from a high (max drawdown): $2,294
- Room left before the $4,000 max drawdown: **$1,706**
- Progress toward a prop demo: **8 of 20** trading days

## By market

| Market | Trades | Wins | Total after fees |
|---|---|---|---|
| nasdaq | 6 | 3 | -$20 |
| gold | 5 | 2 | -$29 |

## Tradeify Growth 50K (practice account the bot trades on)

Rules from Tradeify's help center (Oct 2026): evaluation passes at $53,000; trailing drawdown $2,000 below the highest end-of-day balance, and touching it even with an open trade fails the account; daily loss limit $1,250 ends the day. Funded: a payout needs $53,000, 5 days over $150, and the biggest day at most 35% of the profit. The bot sizes every trade so its stop cannot break a rule, and stops for the day once up $600. Check Tradeify's current rules before relying on this.

**Now: Evaluation**, balance **$49,610**, $1,610 above the drawdown floor.
- To pass: $3,390 more profit.

| # | Account | Started | Ended | Trading days | Balance | Result | Payouts | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | Evaluation | 2026-10-19 | 2026-10-27 | 7 | $50,340 | Failed | – | reset on 2026-10-28: only $96 above the floor, too close for any trade |
| 2 | Evaluation | 2026-10-28 | 2026-10-28 | 1 | $49,610 | In progress | – |  |

## Daily results

| Trading day | Sessions | Result after fees |
|---|---|---|
| 2026-10-28 | gold long | -$390 |
| 2026-10-27 | gold no trade, nasdaq long | -$688 |
| 2026-10-26 | gold short, nasdaq no trade | -$329 |
| 2026-10-23 | gold short, nasdaq long | -$888 |
| 2026-10-22 | gold short, nasdaq short | $1,070 |
| 2026-10-21 | gold no trade, nasdaq short | -$252 |
| 2026-10-20 | gold short, nasdaq long | $1,070 |
| 2026-10-19 | gold no trade, nasdaq long | $357 |

[Every paper trade](paper-journal.md) · [Raw data](trades.csv)
