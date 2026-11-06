# Paper trading summary

*Updated 2026-11-06 11:09 New York time. Paper results from real 5-minute candles with perfect fills at target and stop prices, after $1.00 per contract in fees. Real fills can be worse.*

## At a glance

- Total after fees: **-$708** over 18 trades (29 sessions watched)
- Trading days with a trade: **14**, profitable: **6**, losing: 8
- Win rate: 44%
- Profit factor: 0.85
- Biggest drop from a high (max drawdown): $4,620
- Room left before the $4,000 max drawdown: **$1,047**
- Progress toward a prop demo: **14 of 20** trading days

## By market

| Market | Trades | Wins | Total after fees |
|---|---|---|---|
| nasdaq | 8 | 3 | -$1,716 |
| gold | 10 | 5 | $1,008 |

## Tradeify Growth 50K (practice account the bot trades on)

Rules from Tradeify's help center (Oct 2026): evaluation passes at $53,000; trailing drawdown $2,000 below the highest end-of-day balance, and touching it even with an open trade fails the account; daily loss limit $1,250 ends the day. Funded: a payout needs $53,000, 5 days over $150, and the biggest day at most 35% of the profit. The bot sizes every trade so its stop cannot break a rule, and stops for the day once up $600. Check Tradeify's current rules before relying on this.

**Now: Evaluation**, balance **$50,652**, $2,000 above the drawdown floor.
- To pass: $2,348 more profit.

| # | Account | Started | Ended | Trading days | Balance | Result | Payouts | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | Evaluation | 2026-10-19 | 2026-10-27 | 7 | $50,340 | Failed | – | reset on 2026-10-28: only $96 above the floor, too close for any trade |
| 2 | Evaluation | 2026-10-28 | 2026-10-30 | 3 | $48,299 | Failed | – | reset on 2026-11-02: only $299 above the floor, too close for any trade |
| 3 | Evaluation | 2026-11-02 | 2026-11-06 | 4 | $50,652 | In progress | – |  |

## Opening range (tracked, not traded)

Opening range (9:30-10:00, tracked, not traded): -$515 over 4 trades in 4 sessions since 2026-11-02, vs -$1,015 for the real Nasdaq rule (ahead).

| Day | Range | Trade | Entry | Stop | Out | Result |
|---|---|---|---|---|---|---|
| 2026-11-05 | 27457.5-28228.25 | short | 27344.0 10:10 | 27508.75 | 10:20 | $655 |
| 2026-11-04 | 28405.0-28868.5 | long | 28941.25 10:10 | 28837.75 | 10:20 | -$1,040 |
| 2026-11-03 | 28215.75-28385.75 | long | 28429.25 11:00 | 28351.25 | 11:20 | -$785 |
| 2026-11-02 | 28639.0-28749.5 | long | 28792.25 10:15 | 28703.0 | 10:25 | $655 |

## Daily results

| Trading day | Sessions | Result after fees |
|---|---|---|
| 2026-11-06 | gold short, nasdaq skipped, daily profit cap reached | $655 |
| 2026-11-05 | gold long, nasdaq skipped, daily profit cap reached | $655 |
| 2026-11-04 | gold long, nasdaq skipped, risk too big for today's limits | $357 |
| 2026-11-03 | gold no trade, nasdaq no trade | $0 |
| 2026-11-02 | nasdaq long | -$1,015 |
| 2026-10-30 | gold short, nasdaq skipped, risk too big for today's limits | -$265 |
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
