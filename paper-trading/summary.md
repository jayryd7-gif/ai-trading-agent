# Paper trading summary

*Updated 2026-11-24 04:43 New York time. Paper results from real 5-minute candles with perfect fills at target and stop prices, after $1.00 per contract in fees. Real fills can be worse.*

## At a glance

- Total after fees: **-$1,601** over 34 trades (52 sessions watched)
- Trading days with a trade: **25**, profitable: **10**, losing: 15
- Win rate: 47%
- Profit factor: 0.83
- Biggest drop from a high (max drawdown): $4,620
- Room left before the $4,000 max drawdown: **$154**
- Progress toward a prop demo: **25 of 20** trading days

## By market

| Market | Trades | Wins | Total after fees |
|---|---|---|---|
| nasdaq | 14 | 6 | -$3,302 |
| gold | 20 | 10 | $1,701 |

## Tradeify Growth 50K (practice account the bot trades on)

Rules from Tradeify's help center (Oct 2026): evaluation passes at $53,000; trailing drawdown $2,000 below the highest end-of-day balance, and touching it even with an open trade fails the account; daily loss limit $1,250 ends the day. Funded: a payout needs $53,000, 5 days over $150, and the biggest day at most 35% of the profit. The bot sizes every trade so its stop cannot break a rule (no daily profit cap). Check Tradeify's current rules before relying on this.

**Now: Evaluation**, balance **$49,760**, $634 above the drawdown floor.
- To pass: $3,240 more profit.

| # | Account | Started | Ended | Trading days | Balance | Result | Payouts | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | Evaluation | 2026-10-19 | 2026-10-27 | 7 | $50,340 | Failed | – | reset on 2026-10-28: only $96 above the floor, too close for any trade |
| 2 | Evaluation | 2026-10-28 | 2026-10-30 | 3 | $48,299 | Failed | – | reset on 2026-11-02: only $299 above the floor, too close for any trade |
| 3 | Evaluation | 2026-11-02 | 2026-11-24 | 15 | $49,760 | In progress | – |  |

## Opening range (tracked, not traded)

Opening range (9:30-10:00, tracked, not traded): $2,675 over 13 trades in 16 sessions since 2026-11-02, vs -$2,600 for the real Nasdaq rule (ahead).

| Day | Range | Trade | Entry | Stop | Out | Result |
|---|---|---|---|---|---|---|
| 2026-11-23 | 26450.25-27137.0 | no trade |   |  |  | $0 |
| 2026-11-20 | 26116.75-26451.25 | short | 25995.75 10:20 | 26237.25 | 10:40 | $415 |
| 2026-11-19 | 27620.0-27838.0 | short | 27459.25 10:15 | 27698.25 | 10:25 | $655 |
| 2026-11-18 | 26951.75-27317.75 | no trade |   |  |  | $0 |
| 2026-11-17 | 27197.0-27351.0 | short | 27179.25 10:20 | 27215.75 | 10:25 | -$370 |
| 2026-11-16 | 27485.75-27716.25 | short | 27436.5 10:05 | 27535.0 | 10:25 | $655 |
| 2026-11-13 | 28065.5-28399.0 | short | 27966.25 10:05 | 28096.0 | 10:10 | $655 |
| 2026-11-12 | 28044.5-28398.5 | long | 28536.75 10:55 | 28313.0 | 11:10 | $655 |
| 2026-11-11 | 28199.0-28426.0 | long | 28467.0 10:45 | 28373.75 | 11:05 | $415 |
| 2026-11-10 | 27637.25-28016.75 | long | 28047.0 10:05 | 27993.0 | 10:15 | -$545 |
| 2026-11-09 | 27316.25-27797.5 | long | 27841.25 10:15 | 27749.0 | 10:50 | $655 |
| 2026-11-06 | 27037.75-27425.0 | no trade |   |  |  | $0 |
| 2026-11-05 | 27457.5-28228.25 | short | 27344.0 10:10 | 27508.75 | 10:20 | $655 |
| 2026-11-04 | 28405.0-28868.5 | long | 28941.25 10:10 | 28837.75 | 10:20 | -$1,040 |
| 2026-11-03 | 28215.75-28385.75 | long | 28429.25 11:00 | 28351.25 | 11:20 | -$785 |

## Daily results

| Trading day | Sessions | Result after fees |
|---|---|---|
| 2026-11-24 | gold long | -$680 |
| 2026-11-23 | gold long, nasdaq skipped, risk too big for today's limits | -$605 |
| 2026-11-20 | gold short, nasdaq long | $652 |
| 2026-11-19 | gold no trade, nasdaq skipped, risk too big for today's limits | $0 |
| 2026-11-18 | gold short, nasdaq skipped, risk too big for today's limits | $415 |
| 2026-11-17 | gold short, nasdaq short | -$1,148 |
| 2026-11-16 | gold short, nasdaq short | $892 |
| 2026-11-13 | gold long, nasdaq short | $892 |
| 2026-11-12 | gold long, nasdaq skipped, risk too big for today's limits | -$355 |
| 2026-11-11 | gold long, nasdaq short | -$212 |
| 2026-11-10 | gold no trade, nasdaq long | -$667 |
| 2026-11-09 | gold long, nasdaq skipped, risk too big for today's limits | -$77 |
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
