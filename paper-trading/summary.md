# Paper trading summary

*Updated 2026-10-29 21:56 New York time. Paper results from real 5-minute candles with perfect fills at target and stop prices, after $1.00 per contract in fees. Real fills can be worse.*

## At a glance

- Total after fees: **-$1,360** over 14 trades (19 sessions watched)
- Trading days with a trade: **10**, profitable: **3**, losing: 7
- Win rate: 36%
- Profit factor: 0.65
- Biggest drop from a high (max drawdown): $3,605
- Room left before the $4,000 max drawdown: **$395**
- Progress toward a prop demo: **10 of 20** trading days

## By market

| Market | Trades | Wins | Total after fees |
|---|---|---|---|
| nasdaq | 7 | 3 | -$702 |
| gold | 7 | 2 | -$659 |

## Tradeify Growth 50K (practice account the bot trades on)

Rules from Tradeify's help center (Oct 2026): evaluation passes at $53,000; trailing drawdown $2,000 below the highest end-of-day balance, and touching it even with an open trade fails the account; daily loss limit $1,250 ends the day. Funded: a payout needs $53,000, 5 days over $150, and the biggest day at most 35% of the profit. The bot sizes every trade so its stop cannot break a rule, and stops for the day once up $600. Check Tradeify's current rules before relying on this.

**Now: Evaluation**, balance **$48,299**, $299 above the drawdown floor.
- To pass: $4,701 more profit.

| # | Account | Started | Ended | Trading days | Balance | Result | Payouts | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | Evaluation | 2026-10-19 | 2026-10-27 | 7 | $50,340 | Failed | – | reset on 2026-10-28: only $96 above the floor, too close for any trade |
| 2 | Evaluation | 2026-10-28 | 2026-10-30 | 3 | $48,299 | In progress | – |  |

## Daily results

| Trading day | Sessions | Result after fees |
|---|---|---|
| 2026-10-30 | gold short | -$265 |
| 2026-10-29 | gold short, nasdaq skipped, risk too big for today's limits | -$365 |
| 2026-10-28 | gold long, nasdaq short | -$1,071 |
| 2026-10-27 | gold no trade, nasdaq long | -$688 |
| 2026-10-26 | gold short, nasdaq no trade | -$329 |
| 2026-10-23 | gold short, nasdaq long | -$888 |
| 2026-10-22 | gold short, nasdaq short | $1,070 |
| 2026-10-21 | gold no trade, nasdaq short | -$252 |
| 2026-10-20 | gold short, nasdaq long | $1,070 |
| 2026-10-19 | gold no trade, nasdaq long | $357 |

[Every paper trade](paper-journal.md) · [Raw data](trades.csv)
