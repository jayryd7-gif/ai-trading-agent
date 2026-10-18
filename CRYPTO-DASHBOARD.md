# 🪙 Crypto Dashboard

*Updated 2026-10-18 16:20 UTC with prices up to the close on 2026-10-17. **No real money is used.** Trades happen at daily closing prices (00:00 UTC), after a 0.4% fee. This is research, not financial advice.*

[← Main dashboard](DASHBOARD.md)

## 📄 Paper trading: started 2026-10-17 with $1,000 each

| Bot | Started with | Value now | Total profit / loss | Worst fall | Trades | Holding now |
|---|---|---|---|---|---|---|
| **Rotation bot** | $1,000 | **$996.80** | -$3.20 (-0.3%) | 0% | 4 | AVAX, BCH, BTC, SUI |
| **Buy-and-hold bot** | $1,000 | **$996.00** | -$4.00 (-0.4%) | 0% | 3 | BTC, ETH, SOL |

<!-- ALPACA -->

### 🔄 Rotation bot

Holds up to 5 of the strongest coins by 120-day gain, rechecked every 7 days, only while each coin and bitcoin are above their 50-day averages. Otherwise cash.

**Holding now**

| Coin | Value now | Paid | Profit / loss | Share of the bot |
|---|---|---|---|---|
| AVAX | $199.20 | $200.00 | -$0.80 (-0.4%) | 20% |
| BCH | $199.20 | $200.00 | -$0.80 (-0.4%) | 20% |
| BTC | $199.20 | $200.00 | -$0.80 (-0.4%) | 20% |
| SUI | $199.20 | $200.00 | -$0.80 (-0.4%) | 20% |
| Cash | $200.00 | | | 20% |

**Latest trades**

| Date | | Coin | Price | Amount | Profit / loss | Why |
|---|---|---|---|---|---|---|
| 2026-10-17 | 🟢 Buy | AVAX | $9.77 | $200.00 |  | weekly check: #1 by 120-day gain (+66%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-17 | 🟢 Buy | BCH | $275.50 | $200.00 |  | weekly check: #2 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-17 | 🟢 Buy | BTC | $81,491.04 | $200.00 |  | weekly check: #4 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-17 | 🟢 Buy | SUI | $0.9764 | $200.00 |  | weekly check: #3 by 120-day gain (+36%), in an uptrend, with bitcoin in an uptrend |

**Total**

- **Started with:** $1,000.00
- **Value on 2026-10-17:** $996.80
- **Total profit / loss:** **-$3.20 (-0.3%)**
  - From coins already sold: $0.00 (0 of 0 sells made money)
  - On coins still held: -$3.20
- **Fees paid (included above):** $3.20
- **Trades:** 4 buys, 0 sells

[Journal](crypto/journal-rotation.md)

### 🏦 Buy-and-hold bot

Bought equal thirds of BTC, ETH and SOL on day one and never sells.

**Holding now**

| Coin | Value now | Paid | Profit / loss | Share of the bot |
|---|---|---|---|---|
| BTC | $332.00 | $333.33 | -$1.33 (-0.4%) | 33% |
| ETH | $332.00 | $333.33 | -$1.33 (-0.4%) | 33% |
| SOL | $332.00 | $333.33 | -$1.33 (-0.4%) | 33% |
| Cash | $0.00 | | | 0% |

**Latest trades**

| Date | | Coin | Price | Amount | Profit / loss | Why |
|---|---|---|---|---|---|---|
| 2026-10-17 | 🟢 Buy | BTC | $81,491.04 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good |
| 2026-10-17 | 🟢 Buy | ETH | $2,402.82 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good |
| 2026-10-17 | 🟢 Buy | SOL | $103.47 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good |

**Total**

- **Started with:** $1,000.00
- **Value on 2026-10-17:** $996.00
- **Total profit / loss:** **-$4.00 (-0.4%)**
  - From coins already sold: $0.00 (0 of 0 sells made money)
  - On coins still held: -$4.00
- **Fees paid (included above):** $4.00
- **Trades:** 3 buys, 0 sells

[Journal](crypto/journal-hold.md)

## 📚 Four-year backtest: the same rules from 2022-10-19

What the rules would have done with $1,000 each on real past prices. It keeps running forward alongside the paper accounts.

| Bot | Started with | Value now | Total profit / loss | Worst fall | Trades | Holding now |
|---|---|---|---|---|---|---|
| **Rotation bot** | $1,000 | **$3,325.89** | $2,325.89 (+232.6%) | 49% | 383 | BTC, SUI, AVAX |
| **Buy-and-hold bot** | $1,000 | **$3,225.78** | $2,225.78 (+222.6%) | 64% | 3 | BTC, SOL, ETH |

![Value of each bot](crypto/charts/value.svg)

![What the rotation bot held, and when](crypto/charts/rotation-holdings.svg)

![Drop from each bot's high](crypto/charts/drawdown.svg)

### 🔄 Rotation bot

Holds up to 5 of the strongest coins by 120-day gain, rechecked every 7 days, only while each coin and bitcoin are above their 50-day averages. Otherwise cash.

**Holding now**

| Coin | Value now | Paid | Profit / loss | Share of the bot |
|---|---|---|---|---|
| BTC | $675.68 | $679.98 | -$4.30 (-0.6%) | 20% |
| SUI | $646.60 | $679.98 | -$33.38 (-4.9%) | 19% |
| AVAX | $586.92 | $671.51 | -$84.59 (-12.6%) | 18% |
| Cash | $1,416.70 | | | 43% |

**Latest trades**

| Date | | Coin | Price | Amount | Profit / loss | Why |
|---|---|---|---|---|---|---|
| 2026-10-16 | 🔴 Sell | ADA | $0.2257 | $664.02 | -$18.62 | ADA closed below its 50-day average (its uptrend broke) |
| 2026-10-14 | 🔴 Sell | LINK | $12.44 | $671.03 | $96.37 | LINK closed below its 50-day average (its uptrend broke) |
| 2026-10-14 | 🟢 Buy | ADA | $0.2302 | $679.98 |  | weekly check: #2 by 120-day gain (+34%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-14 | 🟢 Buy | BTC | $81,682.01 | $679.98 |  | weekly check: #4 by 120-day gain (+24%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-14 | 🟢 Buy | SUI | $1.02 | $679.98 |  | weekly check: #3 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-12 | 🔴 Sell | UNI | $6.97 | $907.17 | $331.43 | UNI closed below its 50-day average (its uptrend broke) |
| 2026-10-12 | 🔴 Sell | SOL | $105.76 | $582.12 | $34.57 | SOL closed below its 50-day average (its uptrend broke) |
| 2026-10-08 | 🔴 Sell | ETH | $2,474.80 | $646.18 | -$60.55 | ETH closed below its 50-day average (its uptrend broke) |
| 2026-10-07 | 🔴 Sell | SUI | $1.13 | $674.21 | -$27.00 | no longer one of the top 5 at the weekly check |
| 2026-10-07 | 🟢 Buy | AVAX | $11.13 | $671.51 |  | weekly check: #4 by 120-day gain (+68%), in an uptrend, with bitcoin in an uptrend |

<details>
<summary><b>All 383 trades</b></summary>

| Date | | Coin | Price | Amount | Profit / loss | Why |
|---|---|---|---|---|---|---|
| 2026-10-16 | 🔴 Sell | ADA | $0.2257 | $664.02 | -$18.62 | ADA closed below its 50-day average (its uptrend broke) |
| 2026-10-14 | 🔴 Sell | LINK | $12.44 | $671.03 | $96.37 | LINK closed below its 50-day average (its uptrend broke) |
| 2026-10-14 | 🟢 Buy | ADA | $0.2302 | $679.98 |  | weekly check: #2 by 120-day gain (+34%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-14 | 🟢 Buy | BTC | $81,682.01 | $679.98 |  | weekly check: #4 by 120-day gain (+24%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-14 | 🟢 Buy | SUI | $1.02 | $679.98 |  | weekly check: #3 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend |
| 2026-10-12 | 🔴 Sell | UNI | $6.97 | $907.17 | $331.43 | UNI closed below its 50-day average (its uptrend broke) |
| 2026-10-12 | 🔴 Sell | SOL | $105.76 | $582.12 | $34.57 | SOL closed below its 50-day average (its uptrend broke) |
| 2026-10-08 | 🔴 Sell | ETH | $2,474.80 | $646.18 | -$60.55 | ETH closed below its 50-day average (its uptrend broke) |
| 2026-10-07 | 🔴 Sell | SUI | $1.13 | $674.21 | -$27.00 | no longer one of the top 5 at the weekly check |
| 2026-10-07 | 🟢 Buy | AVAX | $11.13 | $671.51 |  | weekly check: #4 by 120-day gain (+68%), in an uptrend, with bitcoin in an uptrend |
| 2026-09-30 | 🔴 Sell | HYPE | $90.94 | $742.82 | $167.87 | no longer one of the top 5 at the weekly check |
| 2026-09-30 | 🔴 Sell | XLM | $0.2263 | $665.47 | $119.85 | no longer one of the top 5 at the weekly check |
| 2026-09-30 | 🟢 Buy | ETH | $2,686.01 | $704.14 |  | weekly check: #4 by 120-day gain (+44%), in an uptrend, with bitcoin in an uptrend |
| 2026-09-30 | 🟢 Buy | SUI | $1.16 | $698.51 |  | weekly check: #5 by 120-day gain (+44%), in an uptrend, with bitcoin in an uptrend |
| 2026-09-16 | 🔴 Sell | BNB | $725.92 | $565.06 | -$1.97 | no longer one of the top 5 at the weekly check |
| 2026-09-16 | 🟢 Buy | SOL | $98.66 | $545.22 |  | weekly check: #4 by 120-day gain (+17%), in an uptrend, with bitcoin in an uptrend |
| 2026-09-16 | 🟢 Buy | XLM | $0.1839 | $542.96 |  | weekly check: #3 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend |
| 2026-09-10 | 🔴 Sell | XLM | $0.1746 | $527.49 | -$7.26 | XLM closed below its 50-day average (its uptrend broke) |
| 2026-09-09 | 🔴 Sell | SOL | $101.57 | $567.04 | -$7.35 | no longer one of the top 5 at the weekly check |
| 2026-09-09 | 🟢 Buy | BNB | $722.64 | $564.77 |  | weekly check: #5 by 120-day gain (+9%), in an uptrend, with bitcoin in an uptrend |
| 2026-09-02 | 🟢 Buy | XLM | $0.1756 | $532.64 |  | weekly check: #5 by 120-day gain (+10%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-30 | 🔴 Sell | XLM | $0.1746 | $534.78 | -$37.19 | XLM closed below its 50-day average (its uptrend broke) |
| 2026-08-26 | 🔴 Sell | TRX | $0.3360 | $572.41 | -$1.85 | no longer one of the top 5 at the weekly check |
| 2026-08-26 | 🟢 Buy | SOL | $102.07 | $572.12 |  | weekly check: #4 by 120-day gain (+21%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-26 | 🟢 Buy | UNI | $4.38 | $572.12 |  | weekly check: #2 by 120-day gain (+35%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-26 | 🟢 Buy | XLM | $0.1853 | $569.83 |  | weekly check: #5 by 120-day gain (+15%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-19 | 🟢 Buy | HYPE | $69.75 | $571.97 |  | weekly check: #1 by 120-day gain (+75%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-19 | 🟢 Buy | LINK | $10.56 | $571.97 |  | weekly check: #2 by 120-day gain (+12%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-19 | 🟢 Buy | TRX | $0.3344 | $571.97 |  | weekly check: #3 by 120-day gain (+0%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-14 | 🔴 Sell | TRX | $0.3327 | $595.48 | $4.75 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-08-13 | 🔴 Sell | UNI | $3.48 | $503.75 | -$86.61 | UNI closed below its 50-day average (its uptrend broke) |
| 2026-08-05 | 🟢 Buy | TRX | $0.3274 | $588.34 |  | weekly check: #2 by 120-day gain (+4%), in an uptrend, with bitcoin in an uptrend |
| 2026-08-05 | 🟢 Buy | UNI | $4.05 | $588.34 |  | weekly check: #1 by 120-day gain (+23%), in an uptrend, with bitcoin in an uptrend |
| 2026-07-31 | 🔴 Sell | UNI | $4.35 | $658.92 | $80.97 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-07-31 | 🔴 Sell | TRX | $0.3261 | $577.06 | -$4.09 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-07-29 | 🟢 Buy | TRX | $0.3258 | $578.84 |  | weekly check: #2 by 120-day gain (+4%), in an uptrend, with bitcoin in an uptrend |
| 2026-07-28 | 🔴 Sell | TRX | $0.3248 | $565.87 | -$11.71 | TRX closed below its 50-day average (its uptrend broke) |
| 2026-07-22 | 🟢 Buy | TRX | $0.3289 | $575.31 |  | weekly check: #1 by 120-day gain (+7%), in an uptrend, with bitcoin in an uptrend |
| 2026-07-22 | 🟢 Buy | UNI | $3.78 | $575.31 |  | weekly check: #2 by 120-day gain (+5%), in an uptrend, with bitcoin in an uptrend |
| 2026-07-16 | 🔴 Sell | HYPE | $60.70 | $530.79 | -$58.31 | HYPE closed below its 50-day average (its uptrend broke) |
| 2026-07-15 | 🟢 Buy | HYPE | $66.86 | $586.97 |  | weekly check: #1 by 120-day gain (+62%), in an uptrend, with bitcoin in an uptrend |
| 2026-05-22 | 🔴 Sell | TRX | $0.3623 | $694.46 | $79.69 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-05-22 | 🔴 Sell | TON | $1.84 | $465.40 | -$160.76 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-05-22 | 🔴 Sell | HYPE | $54.58 | $593.73 | -$7.57 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-05-20 | 🟢 Buy | HYPE | $54.84 | $598.92 |  | weekly check: #1 by 120-day gain (+161%), in an uptrend, with bitcoin in an uptrend |
| 2026-05-12 | 🔴 Sell | HYPE | $40.26 | $580.43 | -$46.19 | HYPE closed below its 50-day average (its uptrend broke) |
| 2026-05-06 | 🟢 Buy | HYPE | $43.12 | $624.30 |  | weekly check: #1 by 120-day gain (+53%), in an uptrend, with bitcoin in an uptrend |
| 2026-05-06 | 🟢 Buy | TON | $2.45 | $624.30 |  | weekly check: #2 by 120-day gain (+29%), in an uptrend, with bitcoin in an uptrend |
| 2026-04-30 | 🔴 Sell | HYPE | $39.69 | $624.20 | $9.71 | HYPE closed below its 50-day average (its uptrend broke) |
| 2026-04-08 | 🟢 Buy | HYPE | $38.76 | $611.99 |  | weekly check: #1 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend |
| 2026-04-08 | 🟢 Buy | TRX | $0.3180 | $611.99 |  | weekly check: #2 by 120-day gain (+13%), in an uptrend, with bitcoin in an uptrend |
| 2026-03-26 | 🔴 Sell | HYPE | $39.15 | $598.35 | -$22.80 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-03-26 | 🔴 Sell | TRX | $0.3115 | $610.20 | -$10.99 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-03-25 | 🟢 Buy | HYPE | $40.32 | $618.75 |  | weekly check: #1 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend |
| 2026-03-25 | 🟢 Buy | TRX | $0.3146 | $618.75 |  | weekly check: #2 by 120-day gain (+15%), in an uptrend, with bitcoin in an uptrend |
| 2026-03-19 | 🔴 Sell | HYPE | $39.35 | $585.72 | -$45.93 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-03-19 | 🔴 Sell | TRX | $0.3036 | $624.94 | -$6.87 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2026-03-18 | 🟢 Buy | HYPE | $42.11 | $629.31 |  | weekly check: #1 by 120-day gain (+9%), in an uptrend, with bitcoin in an uptrend |
| 2026-03-18 | 🟢 Buy | TRX | $0.3045 | $629.31 |  | weekly check: #2 by 120-day gain (+5%), in an uptrend, with bitcoin in an uptrend |
| 2026-01-14 | 🔴 Sell | BCH | $597.40 | $596.67 | -$36.67 | no longer one of the top 5 at the weekly check |
| 2026-01-14 | 🔴 Sell | BNB | $948.47 | $662.05 | $28.45 | no longer one of the top 5 at the weekly check |
| 2026-01-07 | 🟢 Buy | BCH | $629.20 | $630.95 |  | weekly check: #1 by 120-day gain (+8%), in an uptrend, with bitcoin in an uptrend |
| 2026-01-07 | 🟢 Buy | BNB | $900.30 | $630.95 |  | weekly check: #2 by 120-day gain (+2%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-10 | 🔴 Sell | BNB | $1,102.47 | $739.95 | $45.26 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-10-10 | 🔴 Sell | SOL | $188.43 | $584.67 | -$109.39 | SOL closed below its 50-day average (its uptrend broke) |
| 2025-10-10 | 🔴 Sell | BCH | $513.50 | $566.03 | -$81.57 | BCH closed below its 50-day average (its uptrend broke) |
| 2025-10-09 | 🔴 Sell | XLM | $0.3794 | $656.43 | -$37.92 | XLM closed below its 50-day average (its uptrend broke) |
| 2025-10-09 | 🔴 Sell | ETH | $4,368.09 | $620.36 | -$27.45 | ETH closed below its 50-day average (its uptrend broke) |
| 2025-10-08 | 🟢 Buy | BCH | $583.10 | $645.33 |  | weekly check: #5 by 120-day gain (+33%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-08 | 🟢 Buy | ETH | $4,525.72 | $645.33 |  | weekly check: #2 by 120-day gain (+61%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-07 | 🔴 Sell | AVAX | $27.93 | $626.18 | -$68.05 | AVAX closed below its 50-day average (its uptrend broke) |
| 2025-10-07 | 🔴 Sell | BCH | $576.20 | $669.67 | -$24.74 | BCH closed below its 50-day average (its uptrend broke) |
| 2025-10-01 | 🟢 Buy | AVAX | $30.73 | $691.72 |  | weekly check: #4 by 120-day gain (+45%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-01 | 🟢 Buy | BCH | $592.80 | $691.72 |  | weekly check: #2 by 120-day gain (+48%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-01 | 🟢 Buy | BNB | $1,026.50 | $691.72 |  | weekly check: #1 by 120-day gain (+55%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-01 | 🟢 Buy | SOL | $222.04 | $691.72 |  | weekly check: #5 by 120-day gain (+43%), in an uptrend, with bitcoin in an uptrend |
| 2025-10-01 | 🟢 Buy | XLM | $0.3982 | $691.72 |  | weekly check: #3 by 120-day gain (+46%), in an uptrend, with bitcoin in an uptrend |
| 2025-09-22 | 🔴 Sell | BCH | $567.10 | $692.26 | -$66.34 | BCH closed below its 50-day average (its uptrend broke) |
| 2025-09-22 | 🔴 Sell | BNB | $992.90 | $755.03 | -$3.82 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-09-22 | 🔴 Sell | ETH | $4,199.08 | $688.61 | -$69.97 | ETH closed below its 50-day average (its uptrend broke) |
| 2025-09-22 | 🔴 Sell | HYPE | $47.27 | $616.14 | -$142.16 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-09-21 | 🔴 Sell | LINK | $22.96 | $720.48 | -$38.23 | LINK closed below its 50-day average (its uptrend broke) |
| 2025-09-17 | 🟢 Buy | BCH | $616.70 | $755.83 |  | weekly check: #3 by 120-day gain (+56%), in an uptrend, with bitcoin in an uptrend |
| 2025-09-17 | 🟢 Buy | BNB | $989.98 | $755.83 |  | weekly check: #5 by 120-day gain (+52%), in an uptrend, with bitcoin in an uptrend |
| 2025-09-17 | 🟢 Buy | ETH | $4,590.53 | $755.83 |  | weekly check: #2 by 120-day gain (+82%), in an uptrend, with bitcoin in an uptrend |
| 2025-09-17 | 🟢 Buy | HYPE | $57.75 | $755.83 |  | weekly check: #1 by 120-day gain (+118%), in an uptrend, with bitcoin in an uptrend |
| 2025-09-17 | 🟢 Buy | LINK | $23.99 | $755.83 |  | weekly check: #4 by 120-day gain (+53%), in an uptrend, with bitcoin in an uptrend |
| 2025-08-19 | 🔴 Sell | BCH | $548.50 | $733.55 | $44.61 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-08-19 | 🔴 Sell | ETH | $4,075.59 | $997.32 | $313.08 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-08-19 | 🔴 Sell | UNI | $9.95 | $663.83 | -$20.59 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-08-19 | 🔴 Sell | HYPE | $41.30 | $658.76 | -$107.07 | HYPE closed below its 50-day average (its uptrend broke) |
| 2025-08-19 | 🔴 Sell | LINK | $23.56 | $740.86 | -$19.20 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-08-13 | 🔴 Sell | SUI | $4.00 | $742.75 | $5.68 | no longer one of the top 5 at the weekly check |
| 2025-08-13 | 🔴 Sell | XLM | $0.4519 | $783.65 | $83.91 | no longer one of the top 5 at the weekly check |
| 2025-08-13 | 🟢 Buy | HYPE | $47.65 | $763.20 |  | weekly check: #1 by 120-day gain (+217%), in an uptrend, with bitcoin in an uptrend |
| 2025-08-13 | 🟢 Buy | LINK | $23.98 | $757.09 |  | weekly check: #4 by 120-day gain (+96%), in an uptrend, with bitcoin in an uptrend |
| 2025-08-06 | 🟢 Buy | XLM | $0.4001 | $696.61 |  | weekly check: #5 by 120-day gain (+81%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-31 | 🔴 Sell | HYPE | $40.83 | $699.40 | $10.60 | HYPE closed below its 50-day average (its uptrend broke) |
| 2025-07-23 | 🔴 Sell | XLM | $0.4278 | $684.51 | -$46.45 | no longer one of the top 5 at the weekly check |
| 2025-07-23 | 🟢 Buy | UNI | $10.18 | $681.77 |  | weekly check: #5 by 120-day gain (+46%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-16 | 🔴 Sell | BTC | $118,630.43 | $744.66 | $55.67 | no longer one of the top 5 at the weekly check |
| 2025-07-16 | 🔴 Sell | UNI | $8.90 | $723.53 | $43.17 | no longer one of the top 5 at the weekly check |
| 2025-07-16 | 🟢 Buy | SUI | $3.94 | $734.09 |  | weekly check: #3 by 120-day gain (+73%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-16 | 🟢 Buy | XLM | $0.4533 | $728.22 |  | weekly check: #4 by 120-day gain (+66%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-09 | 🔴 Sell | TRX | $0.2899 | $696.48 | $7.68 | no longer one of the top 5 at the weekly check |
| 2025-07-09 | 🟢 Buy | ETH | $2,768.74 | $680.25 |  | weekly check: #3 by 120-day gain (+44%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-09 | 🟢 Buy | UNI | $8.30 | $677.46 |  | weekly check: #4 by 120-day gain (+36%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-04 | 🔴 Sell | ETH | $2,508.04 | $666.69 | -$21.99 | ETH closed below its 50-day average (its uptrend broke) |
| 2025-07-02 | 🟢 Buy | BCH | $510.90 | $686.01 |  | weekly check: #2 by 120-day gain (+59%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-02 | 🟢 Buy | BTC | $108,849.60 | $686.01 |  | weekly check: #3 by 120-day gain (+25%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-02 | 🟢 Buy | ETH | $2,570.41 | $686.01 |  | weekly check: #4 by 120-day gain (+18%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-02 | 🟢 Buy | HYPE | $39.88 | $686.01 |  | weekly check: #1 by 120-day gain (+133%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-02 | 🟢 Buy | TRX | $0.2844 | $686.01 |  | weekly check: #5 by 120-day gain (+17%), in an uptrend, with bitcoin in an uptrend |
| 2025-07-01 | 🔴 Sell | BCH | $500.20 | $711.00 | $19.13 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-07-01 | 🔴 Sell | BTC | $105,681.14 | $675.66 | -$16.07 | BTC closed below its 50-day average (its uptrend broke) |
| 2025-07-01 | 🔴 Sell | HYPE | $36.92 | $684.38 | -$7.38 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-06-26 | 🔴 Sell | TRX | $0.2710 | $680.99 | -$10.76 | TRX closed below its 50-day average (its uptrend broke) |
| 2025-06-25 | 🟢 Buy | BCH | $482.80 | $689.03 |  | weekly check: #2 by 120-day gain (+65%), in an uptrend, with bitcoin in an uptrend |
| 2025-06-25 | 🟢 Buy | BTC | $107,340.58 | $689.03 |  | weekly check: #3 by 120-day gain (+21%), in an uptrend, with bitcoin in an uptrend |
| 2025-06-25 | 🟢 Buy | HYPE | $37.02 | $689.03 |  | weekly check: #1 by 120-day gain (+83%), in an uptrend, with bitcoin in an uptrend |
| 2025-06-25 | 🟢 Buy | TRX | $0.2731 | $689.03 |  | weekly check: #4 by 120-day gain (+18%), in an uptrend, with bitcoin in an uptrend |
| 2025-06-20 | 🔴 Sell | BTC | $103,297.99 | $722.73 | $58.31 | BTC closed below its 50-day average (its uptrend broke) |
| 2025-06-20 | 🔴 Sell | HYPE | $33.37 | $889.28 | $211.66 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-06-20 | 🔴 Sell | TRX | $0.2722 | $665.50 | -$11.23 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-06-20 | 🔴 Sell | BCH | $473.70 | $647.42 | $56.29 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2025-06-18 | 🔴 Sell | ETH | $2,525.00 | $534.03 | -$56.65 | no longer one of the top 5 at the weekly check |
| 2025-06-11 | 🟢 Buy | BCH | $428.90 | $588.55 |  | weekly check: #2 by 120-day gain (+29%), in an uptrend, with bitcoin in an uptrend |
| 2025-06-11 | 🟢 Buy | ETH | $2,771.61 | $588.55 |  | weekly check: #5 by 120-day gain (+6%), in an uptrend, with bitcoin in an uptrend |
| 2025-06-05 | 🔴 Sell | BCH | $385.00 | $585.83 | -$65.50 | BCH closed below its 50-day average (its uptrend broke) |
| 2025-06-05 | 🔴 Sell | BNB | $633.32 | $595.98 | -$55.39 | BNB closed below its 50-day average (its uptrend broke) |
| 2025-05-28 | 🟢 Buy | BCH | $424.80 | $648.99 |  | weekly check: #5 by 120-day gain (+3%), in an uptrend, with bitcoin in an uptrend |
| 2025-05-28 | 🟢 Buy | BNB | $686.89 | $648.99 |  | weekly check: #4 by 120-day gain (+4%), in an uptrend, with bitcoin in an uptrend |
| 2025-05-14 | 🟢 Buy | HYPE | $25.19 | $674.06 |  | weekly check: #2 by 120-day gain (+10%), in an uptrend, with bitcoin in an uptrend |
| 2025-05-14 | 🟢 Buy | TRX | $0.2746 | $674.06 |  | weekly check: #1 by 120-day gain (+24%), in an uptrend, with bitcoin in an uptrend |
| 2025-04-30 | 🟢 Buy | BTC | $94,172.00 | $661.53 |  | weekly check: #1 by 120-day gain (+1%), in an uptrend, with bitcoin in an uptrend |
| 2025-02-02 | 🔴 Sell | XRP | $2.58 | $690.89 | -$156.88 | XRP closed below its 50-day average (its uptrend broke) |
| 2025-02-02 | 🔴 Sell | SOL | $203.51 | $608.92 | -$166.65 | SOL closed below its 50-day average (its uptrend broke) |
| 2025-02-02 | 🔴 Sell | BTC | $97,700.59 | $666.84 | -$46.69 | BTC closed below its 50-day average (its uptrend broke) |
| 2025-02-02 | 🔴 Sell | LTC | $109.12 | $666.60 | -$46.93 | LTC closed below its 50-day average (its uptrend broke) |
| 2025-02-01 | 🔴 Sell | LINK | $22.98 | $687.67 | -$25.94 | LINK closed below its 50-day average (its uptrend broke) |
| 2025-01-29 | 🟢 Buy | BTC | $103,733.24 | $710.86 |  | weekly check: #4 by 120-day gain (+71%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-29 | 🟢 Buy | LINK | $23.66 | $710.86 |  | weekly check: #2 by 120-day gain (+115%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-29 | 🟢 Buy | LTC | $115.90 | $710.86 |  | weekly check: #3 by 120-day gain (+83%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-28 | 🔴 Sell | LINK | $22.61 | $688.17 | -$87.72 | LINK closed below its 50-day average (its uptrend broke) |
| 2025-01-28 | 🔴 Sell | LTC | $109.92 | $733.60 | -$42.47 | LTC closed below its 50-day average (its uptrend broke) |
| 2025-01-25 | 🔴 Sell | XLM | $0.4172 | $719.38 | -$128.51 | XLM closed below its 50-day average (its uptrend broke) |
| 2025-01-22 | 🟢 Buy | LINK | $25.30 | $773.13 |  | weekly check: #3 by 120-day gain (+108%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-22 | 🟢 Buy | LTC | $115.38 | $773.13 |  | weekly check: #4 by 120-day gain (+73%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-22 | 🟢 Buy | SOL | $257.36 | $773.13 |  | weekly check: #5 by 120-day gain (+69%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-20 | 🔴 Sell | SUI | $4.42 | $768.92 | -$79.17 | SUI closed below its 50-day average (its uptrend broke) |
| 2025-01-19 | 🔴 Sell | ADA | $0.9930 | $777.07 | -$71.05 | ADA closed below its 50-day average (its uptrend broke) |
| 2025-01-19 | 🔴 Sell | DOGE | $0.3584 | $782.73 | -$65.41 | DOGE closed below its 50-day average (its uptrend broke) |
| 2025-01-15 | 🟢 Buy | ADA | $1.08 | $845.01 |  | weekly check: #5 by 120-day gain (+222%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-15 | 🟢 Buy | DOGE | $0.3854 | $845.01 |  | weekly check: #4 by 120-day gain (+281%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-15 | 🟢 Buy | SUI | $4.84 | $845.01 |  | weekly check: #3 by 120-day gain (+314%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-15 | 🟢 Buy | XLM | $0.4881 | $845.01 |  | weekly check: #2 by 120-day gain (+416%), in an uptrend, with bitcoin in an uptrend |
| 2025-01-15 | 🟢 Buy | XRP | $3.14 | $845.01 |  | weekly check: #1 by 120-day gain (+438%), in an uptrend, with bitcoin in an uptrend |
| 2024-12-27 | 🔴 Sell | SUI | $4.08 | $827.07 | $400.34 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-12-27 | 🔴 Sell | XRP | $2.15 | $1,105.45 | $530.16 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-12-27 | 🔴 Sell | UNI | $13.35 | $865.19 | -$43.24 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-12-26 | 🔴 Sell | ADA | $0.8611 | $619.21 | $38.93 | ADA closed below its 50-day average (its uptrend broke) |
| 2024-12-26 | 🔴 Sell | XLM | $0.3547 | $825.09 | $243.99 | XLM closed below its 50-day average (its uptrend broke) |
| 2024-12-25 | 🟢 Buy | UNI | $13.91 | $904.96 |  | weekly check: #5 by 120-day gain (+143%), in an uptrend, with bitcoin in an uptrend |
| 2024-12-19 | 🔴 Sell | DOGE | $0.3143 | $908.60 | $498.72 | DOGE closed below its 50-day average (its uptrend broke) |
| 2024-11-20 | 🔴 Sell | SOL | $235.48 | $643.69 | $217.69 | no longer one of the top 5 at the weekly check |
| 2024-11-20 | 🔴 Sell | TRX | $0.1947 | $512.87 | $87.40 | no longer one of the top 5 at the weekly check |
| 2024-11-20 | 🔴 Sell | BTC | $94,286.56 | $576.85 | $165.02 | no longer one of the top 5 at the weekly check |
| 2024-11-20 | 🟢 Buy | ADA | $0.8003 | $577.80 |  | weekly check: #4 by 120-day gain (+95%), in an uptrend, with bitcoin in an uptrend |
| 2024-11-20 | 🟢 Buy | XLM | $0.2474 | $577.80 |  | weekly check: #3 by 120-day gain (+145%), in an uptrend, with bitcoin in an uptrend |
| 2024-11-20 | 🟢 Buy | XRP | $1.10 | $570.87 |  | weekly check: #5 by 120-day gain (+85%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-23 | 🔴 Sell | AVAX | $26.75 | $402.61 | -$22.42 | no longer one of the top 5 at the weekly check |
| 2024-10-23 | 🔴 Sell | XLM | $0.0944 | $416.43 | -$8.65 | no longer one of the top 5 at the weekly check |
| 2024-10-23 | 🟢 Buy | BTC | $66,668.65 | $409.52 |  | weekly check: #5 by 120-day gain (+8%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-23 | 🟢 Buy | DOGE | $0.1400 | $406.25 |  | weekly check: #4 by 120-day gain (+11%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-16 | 🟢 Buy | AVAX | $28.02 | $423.42 |  | weekly check: #4 by 120-day gain (+5%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-16 | 🟢 Buy | SOL | $154.28 | $423.42 |  | weekly check: #3 by 120-day gain (+12%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-16 | 🟢 Buy | SUI | $2.08 | $423.42 |  | weekly check: #1 by 120-day gain (+160%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-16 | 🟢 Buy | TRX | $0.1601 | $423.42 |  | weekly check: #2 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-16 | 🟢 Buy | XLM | $0.0956 | $423.42 |  | weekly check: #5 by 120-day gain (+5%), in an uptrend, with bitcoin in an uptrend |
| 2024-10-09 | 🔴 Sell | SUI | $1.88 | $558.07 | $163.25 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-10-09 | 🔴 Sell | TRX | $0.1605 | $419.51 | $25.24 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-10-02 | 🔴 Sell | XRP | $0.5383 | $359.68 | -$34.35 | XRP closed below its 50-day average (its uptrend broke) |
| 2024-09-18 | 🟢 Buy | SUI | $1.31 | $392.59 |  | weekly check: #2 by 120-day gain (+15%), in an uptrend, with bitcoin in an uptrend |
| 2024-09-18 | 🟢 Buy | TRX | $0.1496 | $392.59 |  | weekly check: #1 by 120-day gain (+21%), in an uptrend, with bitcoin in an uptrend |
| 2024-09-18 | 🟢 Buy | XRP | $0.5852 | $392.59 |  | weekly check: #3 by 120-day gain (+9%), in an uptrend, with bitcoin in an uptrend |
| 2024-08-02 | 🔴 Sell | TRX | $0.1236 | $381.83 | -$34.02 | TRX closed below its 50-day average (its uptrend broke) |
| 2024-08-02 | 🔴 Sell | BNB | $542.90 | $384.79 | -$26.99 | BNB closed below its 50-day average (its uptrend broke) |
| 2024-08-02 | 🔴 Sell | XRP | $0.5607 | $367.74 | -$43.97 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-07-31 | 🟢 Buy | BNB | $576.50 | $410.24 |  | weekly check: #3 by 120-day gain (+5%), in an uptrend, with bitcoin in an uptrend |
| 2024-07-31 | 🟢 Buy | XRP | $0.6230 | $410.24 |  | weekly check: #2 by 120-day gain (+6%), in an uptrend, with bitcoin in an uptrend |
| 2024-07-24 | 🔴 Sell | BTC | $65,376.00 | $420.96 | $4.95 | no longer one of the top 5 at the weekly check |
| 2024-07-24 | 🔴 Sell | XRP | $0.6179 | $407.33 | -$8.63 | no longer one of the top 5 at the weekly check |
| 2024-07-17 | 🟢 Buy | BTC | $64,087.99 | $414.32 |  | weekly check: #3 by 120-day gain (+3%), in an uptrend, with bitcoin in an uptrend |
| 2024-07-17 | 🟢 Buy | TRX | $0.1336 | $414.32 |  | weekly check: #1 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend |
| 2024-07-17 | 🟢 Buy | XRP | $0.6260 | $414.32 |  | weekly check: #2 by 120-day gain (+7%), in an uptrend, with bitcoin in an uptrend |
| 2024-06-18 | 🔴 Sell | UNI | $9.77 | $423.47 | -$32.87 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-06-18 | 🔴 Sell | BTC | $65,175.32 | $406.79 | -$22.62 | BTC closed below its 50-day average (its uptrend broke) |
| 2024-06-18 | 🔴 Sell | ETH | $3,483.42 | $416.89 | -$12.56 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-06-13 | 🔴 Sell | BNB | $599.80 | $412.59 | -$16.84 | BNB closed below its 50-day average (its uptrend broke) |
| 2024-06-12 | 🟢 Buy | BNB | $619.40 | $427.78 |  | weekly check: #1 by 120-day gain (+91%), in an uptrend, with bitcoin in an uptrend |
| 2024-06-12 | 🟢 Buy | BTC | $68,263.99 | $427.78 |  | weekly check: #3 by 120-day gain (+37%), in an uptrend, with bitcoin in an uptrend |
| 2024-06-12 | 🟢 Buy | ETH | $3,560.12 | $427.78 |  | weekly check: #4 by 120-day gain (+35%), in an uptrend, with bitcoin in an uptrend |
| 2024-06-11 | 🔴 Sell | SOL | $149.31 | $429.13 | -$30.02 | SOL closed below its 50-day average (its uptrend broke) |
| 2024-06-11 | 🔴 Sell | BNB | $602.50 | $438.54 | -$12.50 | BNB closed below its 50-day average (its uptrend broke) |
| 2024-06-08 | 🔴 Sell | BCH | $469.50 | $442.19 | -$27.85 | BCH closed below its 50-day average (its uptrend broke) |
| 2024-06-07 | 🔴 Sell | DOGE | $0.1482 | $398.84 | -$52.05 | DOGE closed below its 50-day average (its uptrend broke) |
| 2024-06-05 | 🔴 Sell | ETH | $3,865.99 | $461.07 | $11.66 | no longer one of the top 5 at the weekly check |
| 2024-06-05 | 🟢 Buy | BCH | $495.20 | $468.27 |  | weekly check: #2 by 120-day gain (+111%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-29 | 🔴 Sell | BTC | $67,652.42 | $465.55 | $6.26 | no longer one of the top 5 at the weekly check |
| 2024-05-29 | 🟢 Buy | UNI | $10.44 | $454.64 |  | weekly check: #3 by 120-day gain (+67%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-22 | 🔴 Sell | TRX | $0.1201 | $433.02 | -$26.14 | no longer one of the top 5 at the weekly check |
| 2024-05-22 | 🟢 Buy | BNB | $614.80 | $449.29 |  | weekly check: #3 by 120-day gain (+106%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-22 | 🟢 Buy | DOGE | $0.1663 | $449.29 |  | weekly check: #1 by 120-day gain (+113%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-22 | 🟢 Buy | ETH | $3,737.73 | $447.56 |  | weekly check: #5 by 120-day gain (+67%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-15 | 🟢 Buy | BTC | $66,206.50 | $457.43 |  | weekly check: #2 by 120-day gain (+53%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-15 | 🟢 Buy | SOL | $158.52 | $457.43 |  | weekly check: #1 by 120-day gain (+62%), in an uptrend, with bitcoin in an uptrend |
| 2024-05-15 | 🟢 Buy | TRX | $0.1263 | $457.43 |  | weekly check: #3 by 120-day gain (+17%), in an uptrend, with bitcoin in an uptrend |
| 2024-04-13 | 🔴 Sell | BNB | $553.10 | $449.27 | -$66.72 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-04-13 | 🔴 Sell | BCH | $479.60 | $395.85 | -$52.48 | BCH closed below its 50-day average (its uptrend broke) |
| 2024-04-13 | 🔴 Sell | BTC | $63,924.51 | $444.34 | -$17.79 | BTC closed below its 50-day average (its uptrend broke) |
| 2024-04-13 | 🔴 Sell | DOGE | $0.1525 | $395.97 | -$62.28 | DOGE closed below its 50-day average (its uptrend broke) |
| 2024-04-12 | 🔴 Sell | SOL | $153.16 | $610.89 | $203.42 | SOL closed below its 50-day average (its uptrend broke) |
| 2024-04-03 | 🔴 Sell | AVAX | $45.89 | $457.29 | $51.96 | AVAX closed below its 50-day average (its uptrend broke) |
| 2024-04-03 | 🔴 Sell | SUI | $1.67 | $463.42 | -$27.59 | SUI closed below its 50-day average (its uptrend broke) |
| 2024-04-03 | 🟢 Buy | BTC | $65,963.28 | $460.35 |  | weekly check: #5 by 120-day gain (+50%), in an uptrend, with bitcoin in an uptrend |
| 2024-04-03 | 🟢 Buy | DOGE | $0.1752 | $456.67 |  | weekly check: #4 by 120-day gain (+86%), in an uptrend, with bitcoin in an uptrend |
| 2024-03-27 | 🔴 Sell | UNI | $12.25 | $448.54 | $44.91 | no longer one of the top 5 at the weekly check |
| 2024-03-27 | 🟢 Buy | BCH | $539.10 | $446.74 |  | weekly check: #5 by 120-day gain (+141%), in an uptrend, with bitcoin in an uptrend |
| 2024-03-20 | 🟢 Buy | SUI | $1.75 | $489.15 |  | weekly check: #2 by 120-day gain (+249%), in an uptrend, with bitcoin in an uptrend |
| 2024-03-14 | 🔴 Sell | SUI | $1.57 | $491.12 | -$20.93 | SUI closed below its 50-day average (its uptrend broke) |
| 2024-03-13 | 🔴 Sell | ADA | $0.7638 | $615.08 | $146.26 | no longer one of the top 5 at the weekly check |
| 2024-03-13 | 🔴 Sell | DOGE | $0.1690 | $413.31 | $24.02 | no longer one of the top 5 at the weekly check |
| 2024-03-13 | 🟢 Buy | BNB | $630.50 | $514.20 |  | weekly check: #5 by 120-day gain (+160%), in an uptrend, with bitcoin in an uptrend |
| 2024-03-13 | 🟢 Buy | SUI | $1.62 | $510.08 |  | weekly check: #3 by 120-day gain (+186%), in an uptrend, with bitcoin in an uptrend |
| 2024-03-06 | 🟢 Buy | DOGE | $0.1578 | $387.64 |  | weekly check: #4 by 120-day gain (+115%), in an uptrend, with bitcoin in an uptrend |
| 2024-03-04 | 🔴 Sell | SUI | $1.49 | $389.19 | -$17.39 | SUI closed below its 50-day average (its uptrend broke) |
| 2024-02-28 | 🔴 Sell | LINK | $19.43 | $416.55 | $9.86 | no longer one of the top 5 at the weekly check |
| 2024-02-28 | 🟢 Buy | AVAX | $40.33 | $403.50 |  | weekly check: #2 by 120-day gain (+256%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-28 | 🟢 Buy | UNI | $10.93 | $401.83 |  | weekly check: #4 by 120-day gain (+163%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-23 | 🔴 Sell | AVAX | $35.92 | $392.02 | -$72.17 | AVAX closed below its 50-day average (its uptrend broke) |
| 2024-02-14 | 🔴 Sell | BTC | $51,795.17 | $471.13 | $64.22 | no longer one of the top 5 at the weekly check |
| 2024-02-14 | 🔴 Sell | ETH | $2,774.81 | $461.58 | $54.71 | no longer one of the top 5 at the weekly check |
| 2024-02-14 | 🟢 Buy | ADA | $0.5768 | $466.36 |  | weekly check: #5 by 120-day gain (+134%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-14 | 🟢 Buy | AVAX | $42.22 | $462.63 |  | weekly check: #3 by 120-day gain (+364%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-07 | 🟢 Buy | BTC | $44,349.60 | $405.03 |  | weekly check: #4 by 120-day gain (+62%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-07 | 🟢 Buy | ETH | $2,425.10 | $405.03 |  | weekly check: #5 by 120-day gain (+55%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-07 | 🟢 Buy | LINK | $18.82 | $405.03 |  | weekly check: #3 by 120-day gain (+159%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-07 | 🟢 Buy | SOL | $101.14 | $405.03 |  | weekly check: #1 by 120-day gain (+357%), in an uptrend, with bitcoin in an uptrend |
| 2024-02-07 | 🟢 Buy | SUI | $1.54 | $405.03 |  | weekly check: #2 by 120-day gain (+271%), in an uptrend, with bitcoin in an uptrend |
| 2024-01-14 | 🔴 Sell | SOL | $93.81 | $736.61 | $551.32 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-01-14 | 🔴 Sell | AVAX | $35.29 | $388.03 | $157.96 | AVAX closed below its 50-day average (its uptrend broke) |
| 2024-01-14 | 🔴 Sell | SUI | $1.25 | $439.21 | $139.96 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2024-01-14 | 🔴 Sell | ADA | $0.5251 | $233.82 | -$20.16 | ADA closed below its 50-day average (its uptrend broke) |
| 2024-01-12 | 🔴 Sell | LINK | $14.15 | $235.59 | -$17.28 | LINK closed below its 50-day average (its uptrend broke) |
| 2024-01-10 | 🔴 Sell | BTC | $46,653.99 | $278.24 | $50.44 | no longer one of the top 5 at the weekly check |
| 2024-01-10 | 🟢 Buy | ADA | $0.5660 | $253.05 |  | weekly check: #4 by 120-day gain (+131%), in an uptrend, with bitcoin in an uptrend |
| 2024-01-10 | 🟢 Buy | LINK | $15.07 | $251.93 |  | weekly check: #3 by 120-day gain (+153%), in an uptrend, with bitcoin in an uptrend |
| 2024-01-07 | 🔴 Sell | ADA | $0.4945 | $228.77 | $22.13 | ADA closed below its 50-day average (its uptrend broke) |
| 2024-01-03 | 🟢 Buy | SUI | $0.8437 | $297.50 |  | weekly check: #4 by 120-day gain (+72%), in an uptrend, with bitcoin in an uptrend |
| 2023-12-31 | 🔴 Sell | LINK | $14.94 | $298.70 | -$37.88 | LINK closed below its 50-day average (its uptrend broke) |
| 2023-12-27 | 🔴 Sell | DOGE | $0.0936 | $336.73 | $5.06 | no longer one of the top 5 at the weekly check |
| 2023-12-27 | 🟢 Buy | LINK | $16.71 | $335.38 |  | weekly check: #3 by 120-day gain (+170%), in an uptrend, with bitcoin in an uptrend |
| 2023-12-20 | 🟢 Buy | DOGE | $0.0915 | $330.32 |  | weekly check: #5 by 120-day gain (+46%), in an uptrend, with bitcoin in an uptrend |
| 2023-12-17 | 🔴 Sell | LINK | $14.01 | $331.65 | $147.97 | LINK closed below its 50-day average (its uptrend broke) |
| 2023-12-06 | 🔴 Sell | TRX | $0.1048 | $206.55 | $0.98 | no longer one of the top 5 at the weekly check |
| 2023-12-06 | 🟢 Buy | ADA | $0.4429 | $205.72 |  | weekly check: #4 by 120-day gain (+49%), in an uptrend, with bitcoin in an uptrend |
| 2023-11-29 | 🔴 Sell | ADA | $0.3816 | $205.57 | -$1.05 | no longer one of the top 5 at the weekly check |
| 2023-11-29 | 🟢 Buy | TRX | $0.1034 | $204.74 |  | weekly check: #4 by 120-day gain (+31%), in an uptrend, with bitcoin in an uptrend |
| 2023-11-22 | 🔴 Sell | TRX | $0.1012 | $206.62 | $23.45 | no longer one of the top 5 at the weekly check |
| 2023-11-22 | 🟢 Buy | ADA | $0.3805 | $205.80 |  | weekly check: #5 by 120-day gain (+25%), in an uptrend, with bitcoin in an uptrend |
| 2023-11-15 | 🔴 Sell | XRP | $0.6481 | $229.36 | $31.17 | no longer one of the top 5 at the weekly check |
| 2023-11-15 | 🔴 Sell | XLM | $0.1214 | $227.68 | -$3.90 | no longer one of the top 5 at the weekly check |
| 2023-11-15 | 🟢 Buy | AVAX | $20.70 | $228.52 |  | weekly check: #3 by 120-day gain (+50%), in an uptrend, with bitcoin in an uptrend |
| 2023-11-15 | 🟢 Buy | BTC | $37,858.20 | $226.69 |  | weekly check: #5 by 120-day gain (+27%), in an uptrend, with bitcoin in an uptrend |
| 2023-11-01 | 🔴 Sell | BTC | $35,421.43 | $231.59 | $48.31 | no longer one of the top 5 at the weekly check |
| 2023-11-01 | 🟢 Buy | XLM | $0.1225 | $230.66 |  | weekly check: #5 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend |
| 2023-10-25 | 🔴 Sell | BCH | $254.20 | $198.06 | $14.92 | no longer one of the top 5 at the weekly check |
| 2023-10-25 | 🟢 Buy | XRP | $0.5552 | $197.27 |  | weekly check: #4 by 120-day gain (+15%), in an uptrend, with bitcoin in an uptrend |
| 2023-10-04 | 🟢 Buy | BCH | $233.10 | $182.35 |  | weekly check: #1 by 120-day gain (+103%), in an uptrend, with bitcoin in an uptrend |
| 2023-10-04 | 🟢 Buy | BTC | $27,778.57 | $182.35 |  | weekly check: #5 by 120-day gain (+2%), in an uptrend, with bitcoin in an uptrend |
| 2023-10-04 | 🟢 Buy | LINK | $7.67 | $182.35 |  | weekly check: #2 by 120-day gain (+23%), in an uptrend, with bitcoin in an uptrend |
| 2023-10-04 | 🟢 Buy | SOL | $23.13 | $182.35 |  | weekly check: #4 by 120-day gain (+13%), in an uptrend, with bitcoin in an uptrend |
| 2023-10-04 | 🟢 Buy | TRX | $0.0889 | $182.35 |  | weekly check: #3 by 120-day gain (+14%), in an uptrend, with bitcoin in an uptrend |
| 2023-07-30 | 🔴 Sell | BCH | $253.00 | $213.15 | $21.89 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-07-30 | 🔴 Sell | TRX | $0.0800 | $185.05 | $3.51 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-07-30 | 🔴 Sell | SOL | $24.25 | $172.01 | -$16.05 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-07-30 | 🔴 Sell | XLM | $0.1565 | $186.75 | -$1.38 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-07-30 | 🔴 Sell | XRP | $0.7046 | $158.46 | -$27.30 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-07-19 | 🔴 Sell | BTC | $29,909.21 | $192.45 | -$2.09 | no longer one of the top 5 at the weekly check |
| 2023-07-19 | 🔴 Sell | ETH | $1,888.63 | $192.95 | -$1.60 | no longer one of the top 5 at the weekly check |
| 2023-07-19 | 🔴 Sell | LTC | $91.99 | $176.73 | -$21.88 | no longer one of the top 5 at the weekly check |
| 2023-07-19 | 🟢 Buy | SOL | $26.31 | $187.38 |  | weekly check: #5 by 120-day gain (+17%), in an uptrend, with bitcoin in an uptrend |
| 2023-07-19 | 🟢 Buy | XLM | $0.1564 | $187.38 |  | weekly check: #3 by 120-day gain (+62%), in an uptrend, with bitcoin in an uptrend |
| 2023-07-19 | 🟢 Buy | XRP | $0.8199 | $185.13 |  | weekly check: #2 by 120-day gain (+75%), in an uptrend, with bitcoin in an uptrend |
| 2023-07-12 | 🔴 Sell | XLM | $0.0961 | $181.52 | -$9.61 | no longer one of the top 5 at the weekly check |
| 2023-07-12 | 🟢 Buy | TRX | $0.0778 | $180.79 |  | weekly check: #3 by 120-day gain (+16%), in an uptrend, with bitcoin in an uptrend |
| 2023-07-05 | 🔴 Sell | TRX | $0.0771 | $198.18 | $6.98 | no longer one of the top 5 at the weekly check |
| 2023-07-05 | 🟢 Buy | LTC | $102.60 | $197.91 |  | weekly check: #5 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend |
| 2023-06-28 | 🟢 Buy | BCH | $225.10 | $190.40 |  | weekly check: #1 by 120-day gain (+71%), in an uptrend, with bitcoin in an uptrend |
| 2023-06-28 | 🟢 Buy | TRX | $0.0737 | $190.40 |  | weekly check: #5 by 120-day gain (+7%), in an uptrend, with bitcoin in an uptrend |
| 2023-06-28 | 🟢 Buy | XLM | $0.1004 | $190.40 |  | weekly check: #3 by 120-day gain (+15%), in an uptrend, with bitcoin in an uptrend |
| 2023-06-26 | 🔴 Sell | XRP | $0.4790 | $184.93 | -$9.58 | XRP closed below its 50-day average (its uptrend broke) |
| 2023-06-21 | 🟢 Buy | BTC | $29,993.89 | $193.77 |  | weekly check: #2 by 120-day gain (+23%), in an uptrend, with bitcoin in an uptrend |
| 2023-06-21 | 🟢 Buy | ETH | $1,889.11 | $193.77 |  | weekly check: #3 by 120-day gain (+14%), in an uptrend, with bitcoin in an uptrend |
| 2023-06-21 | 🟢 Buy | XRP | $0.4999 | $193.77 |  | weekly check: #1 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend |
| 2023-05-07 | 🔴 Sell | BTC | $28,430.10 | $193.84 | -$5.63 | BTC closed below its 50-day average (its uptrend broke) |
| 2023-05-07 | 🔴 Sell | ETH | $1,870.40 | $194.30 | -$5.18 | ETH closed below its 50-day average (its uptrend broke) |
| 2023-05-04 | 🔴 Sell | ADA | $0.3873 | $194.54 | -$4.94 | ADA closed below its 50-day average (its uptrend broke) |
| 2023-05-04 | 🔴 Sell | BNB | $323.80 | $196.63 | -$2.86 | BNB closed below its 50-day average (its uptrend broke) |
| 2023-05-04 | 🔴 Sell | SOL | $21.74 | $193.45 | -$6.02 | SOL closed below its 50-day average (its uptrend broke) |
| 2023-05-03 | 🟢 Buy | ADA | $0.3940 | $198.70 |  | weekly check: #4 by 120-day gain (+56%), in an uptrend, with bitcoin in an uptrend |
| 2023-05-03 | 🟢 Buy | BNB | $325.90 | $198.70 |  | weekly check: #5 by 120-day gain (+32%), in an uptrend, with bitcoin in an uptrend |
| 2023-05-03 | 🟢 Buy | BTC | $29,026.16 | $198.70 |  | weekly check: #1 by 120-day gain (+74%), in an uptrend, with bitcoin in an uptrend |
| 2023-05-03 | 🟢 Buy | ETH | $1,905.12 | $198.70 |  | weekly check: #3 by 120-day gain (+57%), in an uptrend, with bitcoin in an uptrend |
| 2023-05-03 | 🟢 Buy | SOL | $22.24 | $198.70 |  | weekly check: #2 by 120-day gain (+66%), in an uptrend, with bitcoin in an uptrend |
| 2023-05-01 | 🔴 Sell | BTC | $28,068.26 | $223.28 | $28.42 | BTC closed below its 50-day average (its uptrend broke) |
| 2023-05-01 | 🔴 Sell | ETH | $1,830.73 | $214.36 | $19.53 | ETH closed below its 50-day average (its uptrend broke) |
| 2023-05-01 | 🔴 Sell | ADA | $0.3868 | $198.14 | -$10.79 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-05-01 | 🔴 Sell | BNB | $328.50 | $180.03 | -$2.60 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-05-01 | 🔴 Sell | XRP | $0.4649 | $181.66 | -$0.24 | XRP closed below its 50-day average (its uptrend broke) |
| 2023-04-26 | 🔴 Sell | SOL | $21.28 | $183.88 | -$23.34 | SOL closed below its 50-day average (its uptrend broke) |
| 2023-04-26 | 🟢 Buy | BNB | $330.60 | $181.91 |  | weekly check: #4 by 120-day gain (+34%), in an uptrend, with bitcoin in an uptrend |
| 2023-04-26 | 🟢 Buy | XRP | $0.4618 | $181.18 |  | weekly check: #5 by 120-day gain (+26%), in an uptrend, with bitcoin in an uptrend |
| 2023-04-21 | 🔴 Sell | AVAX | $16.94 | $180.67 | -$12.80 | AVAX closed below its 50-day average (its uptrend broke) |
| 2023-04-12 | 🔴 Sell | XRP | $0.5049 | $231.52 | $36.63 | no longer one of the top 5 at the weekly check |
| 2023-04-12 | 🔴 Sell | XLM | $0.1036 | $184.76 | -$7.93 | no longer one of the top 5 at the weekly check |
| 2023-04-12 | 🟢 Buy | ADA | $0.4047 | $208.14 |  | weekly check: #5 by 120-day gain (+29%), in an uptrend, with bitcoin in an uptrend |
| 2023-04-12 | 🟢 Buy | SOL | $23.80 | $206.48 |  | weekly check: #1 by 120-day gain (+71%), in an uptrend, with bitcoin in an uptrend |
| 2023-04-05 | 🔴 Sell | ADA | $0.3923 | $198.72 | $4.10 | no longer one of the top 5 at the weekly check |
| 2023-04-05 | 🟢 Buy | AVAX | $18.00 | $192.75 |  | weekly check: #3 by 120-day gain (+32%), in an uptrend, with bitcoin in an uptrend |
| 2023-04-05 | 🟢 Buy | XLM | $0.1072 | $191.95 |  | weekly check: #5 by 120-day gain (+25%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-30 | 🔴 Sell | LTC | $89.06 | $187.52 | -$6.26 | LTC closed below its 50-day average (its uptrend broke) |
| 2023-03-29 | 🔴 Sell | BNB | $313.70 | $197.86 | $3.10 | no longer one of the top 5 at the weekly check |
| 2023-03-29 | 🟢 Buy | ADA | $0.3811 | $193.82 |  | weekly check: #4 by 120-day gain (+23%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-29 | 🟢 Buy | LTC | $91.31 | $193.03 |  | weekly check: #5 by 120-day gain (+20%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-25 | 🔴 Sell | LINK | $7.08 | $190.55 | -$4.18 | LINK closed below its 50-day average (its uptrend broke) |
| 2023-03-22 | 🟢 Buy | LINK | $7.17 | $193.97 |  | weekly check: #5 by 120-day gain (+12%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-22 | 🟢 Buy | XRP | $0.4213 | $193.97 |  | weekly check: #4 by 120-day gain (+12%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-15 | 🟢 Buy | BNB | $306.30 | $193.97 |  | weekly check: #3 by 120-day gain (+11%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-15 | 🟢 Buy | BTC | $24,285.66 | $193.97 |  | weekly check: #1 by 120-day gain (+44%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-15 | 🟢 Buy | ETH | $1,649.96 | $193.97 |  | weekly check: #2 by 120-day gain (+32%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-03 | 🔴 Sell | LTC | $90.56 | $237.41 | $37.84 | LTC closed below its 50-day average (its uptrend broke) |
| 2023-03-03 | 🔴 Sell | BTC | $22,354.34 | $187.62 | -$18.10 | BTC closed below its 50-day average (its uptrend broke) |
| 2023-03-03 | 🔴 Sell | BCH | $126.40 | $189.19 | -$24.96 | BCH closed below its 50-day average (its uptrend broke) |
| 2023-03-03 | 🔴 Sell | ETH | $1,569.45 | $177.96 | -$12.33 | ETH closed below its 50-day average (its uptrend broke) |
| 2023-03-03 | 🔴 Sell | TRX | $0.0672 | $181.54 | -$8.76 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2023-03-01 | 🟢 Buy | ETH | $1,665.22 | $189.58 |  | weekly check: #5 by 120-day gain (+5%), in an uptrend, with bitcoin in an uptrend |
| 2023-03-01 | 🟢 Buy | TRX | $0.0698 | $189.58 |  | weekly check: #4 by 120-day gain (+11%), in an uptrend, with bitcoin in an uptrend |
| 2023-02-25 | 🔴 Sell | AVAX | $17.94 | $188.81 | -$33.32 | AVAX closed below its 50-day average (its uptrend broke) |
| 2023-02-23 | 🔴 Sell | DOGE | $0.0843 | $191.86 | -$13.04 | DOGE closed below its 50-day average (its uptrend broke) |
| 2023-02-22 | 🔴 Sell | ETH | $1,643.14 | $214.25 | $15.53 | no longer one of the top 5 at the weekly check |
| 2023-02-22 | 🟢 Buy | BCH | $142.00 | $213.39 |  | weekly check: #3 by 120-day gain (+26%), in an uptrend, with bitcoin in an uptrend |
| 2023-02-15 | 🔴 Sell | BNB | $317.40 | $209.97 | -$8.86 | no longer one of the top 5 at the weekly check |
| 2023-02-15 | 🟢 Buy | BTC | $24,324.05 | $204.98 |  | weekly check: #4 by 120-day gain (+26%), in an uptrend, with bitcoin in an uptrend |
| 2023-02-15 | 🟢 Buy | DOGE | $0.0893 | $204.14 |  | weekly check: #2 by 120-day gain (+49%), in an uptrend, with bitcoin in an uptrend |
| 2023-02-09 | 🔴 Sell | DOGE | $0.0814 | $200.79 | -$14.23 | DOGE closed below its 50-day average (its uptrend broke) |
| 2023-02-08 | 🔴 Sell | BTC | $22,963.00 | $218.86 | $20.12 | no longer one of the top 5 at the weekly check |
| 2023-02-08 | 🟢 Buy | BNB | $328.20 | $217.98 |  | weekly check: #5 by 120-day gain (+21%), in an uptrend, with bitcoin in an uptrend |
| 2023-02-01 | 🔴 Sell | BCH | $136.20 | $222.26 | $5.43 | no longer one of the top 5 at the weekly check |
| 2023-02-01 | 🟢 Buy | AVAX | $20.95 | $221.37 |  | weekly check: #4 by 120-day gain (+20%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-25 | 🔴 Sell | BNB | $306.90 | $217.85 | $14.00 | no longer one of the top 5 at the weekly check |
| 2023-01-25 | 🔴 Sell | UNI | $6.60 | $214.04 | $16.14 | no longer one of the top 5 at the weekly check |
| 2023-01-25 | 🟢 Buy | BCH | $131.80 | $215.95 |  | weekly check: #5 by 120-day gain (+15%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-25 | 🟢 Buy | DOGE | $0.0865 | $214.22 |  | weekly check: #2 by 120-day gain (+43%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-18 | 🔴 Sell | XRP | $0.3782 | $205.09 | $1.30 | no longer one of the top 5 at the weekly check |
| 2023-01-18 | 🟢 Buy | BTC | $20,677.47 | $197.87 |  | weekly check: #4 by 120-day gain (+10%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-18 | 🟢 Buy | ETH | $1,511.43 | $197.87 |  | weekly check: #2 by 120-day gain (+14%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-18 | 🟢 Buy | UNI | $6.05 | $197.05 |  | weekly check: #3 by 120-day gain (+14%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-11 | 🟢 Buy | BNB | $284.80 | $202.98 |  | weekly check: #3 by 120-day gain (+3%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-11 | 🟢 Buy | XRP | $0.3728 | $202.98 |  | weekly check: #2 by 120-day gain (+12%), in an uptrend, with bitcoin in an uptrend |
| 2023-01-04 | 🟢 Buy | LTC | $75.46 | $198.62 |  | weekly check: #1 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend |
| 2022-11-08 | 🔴 Sell | BNB | $327.40 | $224.73 | $23.84 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2022-11-08 | 🔴 Sell | DOGE | $0.0883 | $242.03 | $41.06 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2022-11-08 | 🔴 Sell | ETH | $1,334.77 | $169.78 | -$30.90 | ETH closed below its 50-day average (its uptrend broke) |
| 2022-11-08 | 🔴 Sell | UNI | $6.07 | $180.74 | -$19.98 | UNI closed below its 50-day average (its uptrend broke) |
| 2022-11-08 | 🔴 Sell | LTC | $57.82 | $179.79 | -$11.21 | bitcoin closed below its 50-day average, so the bot moved to cash |
| 2022-11-02 | 🔴 Sell | XRP | $0.4497 | $191.04 | -$9.72 | XRP closed below its 50-day average (its uptrend broke) |
| 2022-11-02 | 🟢 Buy | LTC | $60.95 | $190.28 |  | weekly check: #5 by 120-day gain (+23%), in an uptrend, with bitcoin in an uptrend |
| 2022-10-26 | 🟢 Buy | BNB | $290.20 | $200.00 |  | weekly check: #4 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend |
| 2022-10-26 | 🟢 Buy | DOGE | $0.0727 | $200.00 |  | weekly check: #5 by 120-day gain (+10%), in an uptrend, with bitcoin in an uptrend |
| 2022-10-26 | 🟢 Buy | ETH | $1,566.10 | $200.00 |  | weekly check: #2 by 120-day gain (+37%), in an uptrend, with bitcoin in an uptrend |
| 2022-10-26 | 🟢 Buy | UNI | $6.69 | $200.00 |  | weekly check: #3 by 120-day gain (+36%), in an uptrend, with bitcoin in an uptrend |
| 2022-10-26 | 🟢 Buy | XRP | $0.4689 | $200.00 |  | weekly check: #1 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend |

</details>

**Total**

- **Started with:** $1,000.00
- **Value on 2026-10-17:** $3,325.89
- **Total profit / loss:** **$2,325.89 (+232.6%)**
  - From coins already sold: $2,448.17 (73 of 190 sells made money)
  - On coins still held: -$122.28
- **Fees paid (included above):** $708.24
- **Trades:** 193 buys, 190 sells

[Journal](crypto/backtest/journal-rotation.md)

### 🏦 Buy-and-hold bot

Bought equal thirds of BTC, ETH and SOL on day one and never sells.

**Holding now**

| Coin | Value now | Paid | Profit / loss | Share of the bot |
|---|---|---|---|---|
| BTC | $1,414.72 | $333.33 | $1,081.38 (+324.4%) | 44% |
| SOL | $1,190.30 | $333.33 | $856.97 (+257.1%) | 37% |
| ETH | $620.76 | $333.33 | $287.43 (+86.2%) | 19% |
| Cash | $0.00 | | | 0% |

**Latest trades**

| Date | | Coin | Price | Amount | Profit / loss | Why |
|---|---|---|---|---|---|---|
| 2022-10-19 | 🟢 Buy | BTC | $19,123.97 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good |
| 2022-10-19 | 🟢 Buy | ETH | $1,285.09 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good |
| 2022-10-19 | 🟢 Buy | SOL | $28.86 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good |

**Total**

- **Started with:** $1,000.00
- **Value on 2026-10-17:** $3,225.78
- **Total profit / loss:** **$2,225.78 (+222.6%)**
  - From coins already sold: $0.00 (0 of 0 sells made money)
  - On coins still held: $2,225.78
- **Fees paid (included above):** $4.00
- **Trades:** 3 buys, 0 sells

[Journal](crypto/backtest/journal-hold.md)

### Month by month (backtest)

Each bot's value at the end of each month.

| Month end | Rotation bot | Buy-and-hold bot |
|---|---|---|
| 2026-10 | $3,326 | $3,226 |
| 2026-09 | $3,978 | $3,504 |
| 2026-08 | $3,087 | $3,187 |
| 2026-07 | $2,942 | $2,411 |
| 2026-06 | $2,935 | $2,271 |
| 2026-05 | $2,935 | $2,746 |
| 2026-04 | $3,084 | $2,864 |
| 2026-03 | $3,060 | $2,686 |
| 2026-02 | $3,147 | $2,641 |
| 2026-01 | $3,147 | $3,215 |
| 2025-12 | $3,155 | $3,723 |
| 2025-11 | $3,155 | $3,877 |
| 2025-10 | $3,155 | $5,051 |
| 2025-09 | $3,459 | $5,451 |
| 2025-08 | $3,779 | $5,322 |
| 2025-07 | $3,646 | $4,946 |
| 2025-06 | $3,505 | $4,283 |
| 2025-05 | $3,504 | $4,269 |
| 2025-04 | $3,305 | $3,796 |
| 2025-03 | $3,308 | $3,337 |
| 2025-02 | $3,308 | $3,747 |
| 2025-01 | $3,741 | $5,297 |
| 2024-12 | $4,225 | $4,665 |
| 2024-11 | $4,924 | $5,364 |
| 2024-10 | $2,201 | $3,812 |
| 2024-09 | $2,129 | $3,526 |
| 2024-08 | $1,963 | $3,230 |
| 2024-07 | $2,048 | $3,932 |
| 2024-06 | $2,072 | $3,665 |
| 2024-05 | $2,226 | $4,050 |
| 2024-04 | $2,287 | $3,290 |
| 2024-03 | $2,931 | $4,508 |
| 2024-02 | $2,283 | $3,370 |
| 2024-01 | $2,025 | $2,444 |
| 2023-12 | $2,047 | $2,494 |
| 2023-11 | $1,471 | $1,867 |
| 2023-10 | $1,207 | $1,512 |
| 2023-09 | $912 | $1,146 |
| 2023-08 | $912 | $1,103 |
| 2023-07 | $912 | $1,260 |
| 2023-06 | $1,055 | $1,246 |
| 2023-05 | $969 | $1,196 |
| 2023-04 | $1,023 | $1,252 |
| 2023-03 | $1,075 | $1,208 |
| 2023-02 | $1,017 | $1,068 |
| 2023-01 | $1,128 | $1,086 |
| 2022-12 | $993 | $711 |
| 2022-11 | $993 | $795 |
| 2022-10 | $1,176 | $1,137 |

## Files

- [Every trade, all accounts (CSV)](crypto/trades.csv)
- [How these strategies were chosen](crypto/STRATEGIES.md)
