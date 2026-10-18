# 🪙 Crypto Dashboard

*Updated 2026-10-18 02:48 UTC with prices up to the close on 2026-10-17. Each bot started with $1,000 on 2024-10-19. Before 2026-10-19 the results are a backtest (what the rules would have done on real prices); from 2026-10-19 on they are paper trades. **No real money is used.** Prices are daily closes, after a 0.4% fee per trade. This is research, not financial advice.*

[← Main dashboard](DASHBOARD.md)

## At a glance

| Bot | Started with | Value now | Return | Worst fall | Trades | Holding now |
|---|---|---|---|---|---|---|
| **Rotation bot** | $1,000 | **$1,626.77** | +62.7% | 50% | 187 | BCH, BTC, DOT, SUI, AVAX |
| **Buy-and-hold bot** | $1,000 | **$911.89** | -8.8% | 63% | 3 | BTC, ETH, SOL |

## Charts

![Value of each bot](crypto/charts/value.svg)

![What the rotation bot held, and when](crypto/charts/rotation-holdings.svg)

![Drop from each bot's high](crypto/charts/drawdown.svg)

## 🔄 Rotation bot

Holds up to 5 of the strongest coins by 120-day gain, rechecked every 7 days, only while each coin and bitcoin are above their 50-day averages. Otherwise cash.

### Holding now

| Coin | Value now | Paid | Profit / loss | Share of the bot |
|---|---|---|---|---|
| BCH | $325.09 | $326.40 | -$1.31 (-0.4%) | 20% |
| BTC | $325.09 | $326.40 | -$1.31 (-0.4%) | 20% |
| DOT | $325.09 | $326.40 | -$1.31 (-0.4%) | 20% |
| SUI | $325.09 | $326.40 | -$1.31 (-0.4%) | 20% |
| AVAX | $278.00 | $296.17 | -$18.18 (-6.1%) | 17% |
| Cash | $48.40 | | | 3% |

### Latest 10 trades

| Date | | Coin | Price | Amount | Profit / loss | Why | Type |
|---|---|---|---|---|---|---|---|
| 2026-10-17 | 🟢 Buy | BCH | $275.50 | $326.40 |  | weekly check: #2 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-17 | 🟢 Buy | BTC | $81,491.04 | $326.40 |  | weekly check: #4 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-17 | 🟢 Buy | DOT | $1.12 | $326.40 |  | weekly check: #5 by 120-day gain (+16%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-17 | 🟢 Buy | SUI | $0.9764 | $326.40 |  | weekly check: #3 by 120-day gain (+36%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-14 | 🔴 Sell | LINK | $12.44 | $322.98 | $17.93 | LINK closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-14 | 🔴 Sell | LTC | $59.28 | $272.05 | -$24.02 | LTC closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-12 | 🔴 Sell | UNI | $6.97 | $490.95 | $185.23 | UNI closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-12 | 🔴 Sell | SOL | $105.76 | $273.45 | $8.19 | SOL closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-10 | 🔴 Sell | SUI | $1.11 | $298.64 | -$21.46 | no longer one of the top 5 at the weekly check | backtest |
| 2026-10-10 | 🟢 Buy | AVAX | $10.36 | $296.17 |  | weekly check: #4 by 120-day gain (+58%), in an uptrend, with bitcoin in an uptrend | backtest |

<details>
<summary><b>All 187 rotation trades</b></summary>

| Date | | Coin | Price | Amount | Profit / loss | Why | Type |
|---|---|---|---|---|---|---|---|
| 2026-10-17 | 🟢 Buy | BCH | $275.50 | $326.40 |  | weekly check: #2 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-17 | 🟢 Buy | BTC | $81,491.04 | $326.40 |  | weekly check: #4 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-17 | 🟢 Buy | DOT | $1.12 | $326.40 |  | weekly check: #5 by 120-day gain (+16%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-17 | 🟢 Buy | SUI | $0.9764 | $326.40 |  | weekly check: #3 by 120-day gain (+36%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-14 | 🔴 Sell | LINK | $12.44 | $322.98 | $17.93 | LINK closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-14 | 🔴 Sell | LTC | $59.28 | $272.05 | -$24.02 | LTC closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-12 | 🔴 Sell | UNI | $6.97 | $490.95 | $185.23 | UNI closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-12 | 🔴 Sell | SOL | $105.76 | $273.45 | $8.19 | SOL closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-10 | 🔴 Sell | SUI | $1.11 | $298.64 | -$21.46 | no longer one of the top 5 at the weekly check | backtest |
| 2026-10-10 | 🟢 Buy | AVAX | $10.36 | $296.17 |  | weekly check: #4 by 120-day gain (+58%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-10 | 🟢 Buy | LTC | $64.02 | $294.98 |  | weekly check: #5 by 120-day gain (+49%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-08 | 🔴 Sell | ETH | $2,474.80 | $294.88 | -$27.78 | ETH closed below its 50-day average (its uptrend broke) | backtest |
| 2026-10-03 | 🔴 Sell | HYPE | $89.28 | $340.15 | $35.04 | no longer one of the top 5 at the weekly check | backtest |
| 2026-10-03 | 🔴 Sell | LTC | $70.29 | $302.81 | -$12.33 | no longer one of the top 5 at the weekly check | backtest |
| 2026-10-03 | 🟢 Buy | ETH | $2,687.23 | $321.48 |  | weekly check: #4 by 120-day gain (+70%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-10-03 | 🟢 Buy | SUI | $1.18 | $318.91 |  | weekly check: #5 by 120-day gain (+68%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-09-26 | 🔴 Sell | XLM | $0.2165 | $315.19 | $50.83 | no longer one of the top 5 at the weekly check | backtest |
| 2026-09-26 | 🟢 Buy | LTC | $72.58 | $313.93 |  | weekly check: #5 by 120-day gain (+40%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-09-12 | 🔴 Sell | BNB | $727.59 | $265.21 | -$16.38 | no longer one of the top 5 at the weekly check | backtest |
| 2026-09-12 | 🟢 Buy | SOL | $101.76 | $264.17 |  | weekly check: #5 by 120-day gain (+14%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-09-12 | 🟢 Buy | XLM | $0.1800 | $263.11 |  | weekly check: #3 by 120-day gain (+16%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-09-10 | 🔴 Sell | XLM | $0.1746 | $264.17 | -$16.25 | XLM closed below its 50-day average (its uptrend broke) | backtest |
| 2026-09-05 | 🔴 Sell | SOL | $103.18 | $292.08 | -$9.25 | no longer one of the top 5 at the weekly check | backtest |
| 2026-09-05 | 🟢 Buy | BNB | $766.53 | $280.53 |  | weekly check: #3 by 120-day gain (+18%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-09-05 | 🟢 Buy | XLM | $0.1839 | $279.36 |  | weekly check: #5 by 120-day gain (+12%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-30 | 🔴 Sell | XLM | $0.1746 | $270.06 | -$34.78 | XLM closed below its 50-day average (its uptrend broke) | backtest |
| 2026-08-29 | 🔴 Sell | BNB | $692.58 | $301.37 | -$3.60 | no longer one of the top 5 at the weekly check | backtest |
| 2026-08-29 | 🟢 Buy | SOL | $105.61 | $300.16 |  | weekly check: #3 by 120-day gain (+26%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-22 | 🟢 Buy | BNB | $695.28 | $303.76 |  | weekly check: #5 by 120-day gain (+9%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-22 | 🟢 Buy | HYPE | $79.41 | $303.76 |  | weekly check: #1 by 120-day gain (+93%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-22 | 🟢 Buy | LINK | $11.65 | $303.76 |  | weekly check: #3 by 120-day gain (+24%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-22 | 🟢 Buy | UNI | $4.30 | $303.76 |  | weekly check: #2 by 120-day gain (+32%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-22 | 🟢 Buy | XLM | $0.1956 | $303.76 |  | weekly check: #4 by 120-day gain (+13%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-14 | 🔴 Sell | TRX | $0.3327 | $314.42 | $0.90 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-08-13 | 🔴 Sell | UNI | $3.48 | $269.90 | -$43.45 | UNI closed below its 50-day average (its uptrend broke) | backtest |
| 2026-08-08 | 🟢 Buy | TRX | $0.3291 | $312.27 |  | weekly check: #2 by 120-day gain (+3%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-08-08 | 🟢 Buy | UNI | $4.01 | $312.27 |  | weekly check: #1 by 120-day gain (+27%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-07-31 | 🔴 Sell | UNI | $4.35 | $358.02 | $53.25 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-07-28 | 🔴 Sell | TRX | $0.3248 | $295.93 | -$8.59 | TRX closed below its 50-day average (its uptrend broke) | backtest |
| 2026-07-25 | 🟢 Buy | TRX | $0.3316 | $303.34 |  | weekly check: #2 by 120-day gain (+7%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-07-25 | 🟢 Buy | UNI | $3.67 | $303.34 |  | weekly check: #1 by 120-day gain (+8%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-05-26 | 🔴 Sell | HYPE | $59.51 | $300.74 | $1.67 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-05-26 | 🔴 Sell | TON | $1.95 | $316.86 | $17.73 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-05-26 | 🔴 Sell | TRX | $0.3756 | $307.05 | $7.96 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-05-23 | 🟢 Buy | HYPE | $58.70 | $297.86 |  | weekly check: #1 by 120-day gain (+159%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-05-23 | 🟢 Buy | TON | $1.82 | $297.86 |  | weekly check: #3 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-05-23 | 🟢 Buy | TRX | $0.3629 | $297.86 |  | weekly check: #2 by 120-day gain (+22%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-05-22 | 🔴 Sell | TRX | $0.3623 | $333.45 | $37.43 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-05-22 | 🔴 Sell | TON | $1.84 | $224.09 | -$75.08 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-05-22 | 🔴 Sell | HYPE | $54.58 | $366.73 | $83.14 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2026-05-16 | 🟢 Buy | HYPE | $41.82 | $282.13 |  | weekly check: #1 by 120-day gain (+67%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-05-12 | 🔴 Sell | HYPE | $40.26 | $284.23 | -$9.35 | HYPE closed below its 50-day average (its uptrend broke) | backtest |
| 2026-05-09 | 🟢 Buy | TON | $2.43 | $298.27 |  | weekly check: #2 by 120-day gain (+39%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-05-02 | 🟢 Buy | HYPE | $41.25 | $292.44 |  | weekly check: #1 by 120-day gain (+68%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-04-30 | 🔴 Sell | HYPE | $39.69 | $275.54 | -$20.25 | HYPE closed below its 50-day average (its uptrend broke) | backtest |
| 2026-04-11 | 🟢 Buy | HYPE | $42.28 | $294.68 |  | weekly check: #1 by 120-day gain (+48%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-04-11 | 🟢 Buy | TRX | $0.3189 | $294.68 |  | weekly check: #2 by 120-day gain (+17%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-01-17 | 🔴 Sell | BCH | $594.10 | $270.44 | -$29.77 | no longer one of the top 5 at the weekly check | backtest |
| 2026-01-10 | 🔴 Sell | BNB | $907.93 | $307.88 | $7.51 | no longer one of the top 5 at the weekly check | backtest |
| 2026-01-03 | 🟢 Buy | BCH | $654.50 | $299.14 |  | weekly check: #1 by 120-day gain (+8%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2026-01-03 | 🟢 Buy | BNB | $878.63 | $299.14 |  | weekly check: #2 by 120-day gain (+3%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-10-10 | 🔴 Sell | BNB | $1,102.47 | $309.45 | -$16.09 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-10-10 | 🔴 Sell | SOL | $188.43 | $267.11 | -$58.26 | SOL closed below its 50-day average (its uptrend broke) | backtest |
| 2025-10-09 | 🔴 Sell | ETH | $4,368.09 | $314.43 | -$11.13 | ETH closed below its 50-day average (its uptrend broke) | backtest |
| 2025-10-09 | 🔴 Sell | XLM | $0.3794 | $311.19 | -$14.35 | XLM closed below its 50-day average (its uptrend broke) | backtest |
| 2025-10-07 | 🔴 Sell | AVAX | $27.93 | $299.52 | -$25.98 | AVAX closed below its 50-day average (its uptrend broke) | backtest |
| 2025-10-04 | 🟢 Buy | AVAX | $30.12 | $324.30 |  | weekly check: #4 by 120-day gain (+53%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-10-04 | 🟢 Buy | BNB | $1,150.75 | $324.30 |  | weekly check: #2 by 120-day gain (+79%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-10-04 | 🟢 Buy | ETH | $4,487.15 | $324.30 |  | weekly check: #1 by 120-day gain (+81%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-10-04 | 🟢 Buy | SOL | $227.86 | $324.30 |  | weekly check: #3 by 120-day gain (+54%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-10-04 | 🟢 Buy | XLM | $0.3938 | $324.30 |  | weekly check: #5 by 120-day gain (+50%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-22 | 🔴 Sell | ETH | $4,199.08 | $316.38 | -$37.90 | ETH closed below its 50-day average (its uptrend broke) | backtest |
| 2025-09-22 | 🔴 Sell | HYPE | $47.27 | $305.54 | -$48.70 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-09-22 | 🔴 Sell | AVAX | $33.86 | $348.64 | $4.34 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-09-22 | 🔴 Sell | BNB | $992.90 | $324.89 | -$19.32 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-09-21 | 🔴 Sell | LINK | $22.96 | $324.47 | -$29.84 | LINK closed below its 50-day average (its uptrend broke) | backtest |
| 2025-09-20 | 🔴 Sell | BCH | $594.50 | $349.25 | -$5.16 | no longer one of the top 5 at the weekly check | backtest |
| 2025-09-20 | 🔴 Sell | SOL | $239.48 | $347.40 | -$7.01 | no longer one of the top 5 at the weekly check | backtest |
| 2025-09-20 | 🟢 Buy | AVAX | $33.17 | $342.91 |  | weekly check: #5 by 120-day gain (+44%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-20 | 🟢 Buy | BNB | $1,043.77 | $342.91 |  | weekly check: #3 by 120-day gain (+59%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-13 | 🟢 Buy | BCH | $598.50 | $353.02 |  | weekly check: #4 by 120-day gain (+51%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-13 | 🟢 Buy | ETH | $4,666.53 | $353.02 |  | weekly check: #2 by 120-day gain (+84%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-13 | 🟢 Buy | HYPE | $54.40 | $353.02 |  | weekly check: #1 by 120-day gain (+103%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-13 | 🟢 Buy | LINK | $24.88 | $353.02 |  | weekly check: #3 by 120-day gain (+58%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-09-13 | 🟢 Buy | SOL | $242.38 | $353.02 |  | weekly check: #5 by 120-day gain (+45%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-08-19 | 🔴 Sell | ETH | $4,075.59 | $432.92 | $117.29 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-08-19 | 🔴 Sell | UNI | $9.95 | $319.90 | -$22.16 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-08-19 | 🔴 Sell | HYPE | $41.30 | $335.93 | -$22.18 | HYPE closed below its 50-day average (its uptrend broke) | backtest |
| 2025-08-19 | 🔴 Sell | LINK | $23.56 | $366.54 | $11.43 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-08-19 | 🔴 Sell | SUI | $3.42 | $316.88 | -$35.19 | SUI closed below its 50-day average (its uptrend broke) | backtest |
| 2025-08-16 | 🔴 Sell | BCH | $587.30 | $353.48 | $56.39 | no longer one of the top 5 at the weekly check | backtest |
| 2025-08-16 | 🔴 Sell | XLM | $0.4265 | $353.79 | $46.64 | no longer one of the top 5 at the weekly check | backtest |
| 2025-08-16 | 🟢 Buy | LINK | $22.64 | $353.64 |  | weekly check: #4 by 120-day gain (+80%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-08-16 | 🟢 Buy | SUI | $3.77 | $350.81 |  | weekly check: #5 by 120-day gain (+78%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-08-09 | 🔴 Sell | SUI | $3.90 | $358.20 | $42.87 | no longer one of the top 5 at the weekly check | backtest |
| 2025-08-09 | 🟢 Buy | HYPE | $43.68 | $356.76 |  | weekly check: #1 by 120-day gain (+179%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-08-02 | 🟢 Buy | XLM | $0.3671 | $305.74 |  | weekly check: #5 by 120-day gain (+41%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-31 | 🔴 Sell | HYPE | $40.83 | $306.97 | $10.06 | HYPE closed below its 50-day average (its uptrend broke) | backtest |
| 2025-07-26 | 🔴 Sell | XLM | $0.4352 | $342.14 | $30.65 | no longer one of the top 5 at the weekly check | backtest |
| 2025-07-26 | 🟢 Buy | UNI | $10.56 | $340.78 |  | weekly check: #4 by 120-day gain (+71%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-12 | 🔴 Sell | BNB | $685.86 | $307.83 | $10.92 | no longer one of the top 5 at the weekly check | backtest |
| 2025-07-12 | 🔴 Sell | BTC | $117,420.00 | $319.60 | $22.64 | no longer one of the top 5 at the weekly check | backtest |
| 2025-07-12 | 🔴 Sell | TRX | $0.3022 | $314.26 | $17.32 | no longer one of the top 5 at the weekly check | backtest |
| 2025-07-12 | 🟢 Buy | ETH | $2,943.28 | $313.90 |  | weekly check: #2 by 120-day gain (+54%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-12 | 🟢 Buy | SUI | $3.40 | $313.90 |  | weekly check: #4 by 120-day gain (+46%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-12 | 🟢 Buy | XLM | $0.3929 | $310.13 |  | weekly check: #5 by 120-day gain (+42%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-05 | 🟢 Buy | BCH | $489.30 | $295.68 |  | weekly check: #2 by 120-day gain (+26%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-05 | 🟢 Buy | BNB | $656.16 | $295.68 |  | weekly check: #5 by 120-day gain (+10%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-05 | 🟢 Buy | BTC | $108,198.12 | $295.68 |  | weekly check: #3 by 120-day gain (+25%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-05 | 🟢 Buy | HYPE | $39.17 | $295.68 |  | weekly check: #1 by 120-day gain (+159%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-05 | 🟢 Buy | TRX | $0.2832 | $295.68 |  | weekly check: #4 by 120-day gain (+16%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-07-01 | 🔴 Sell | BCH | $500.20 | $302.25 | $3.16 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-07-01 | 🔴 Sell | BTC | $105,681.14 | $292.22 | -$6.83 | BTC closed below its 50-day average (its uptrend broke) | backtest |
| 2025-07-01 | 🔴 Sell | HYPE | $36.92 | $289.68 | -$9.37 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-07-01 | 🔴 Sell | TRX | $0.2788 | $301.12 | $2.03 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-06-28 | 🟢 Buy | BCH | $491.00 | $297.88 |  | weekly check: #2 by 120-day gain (+55%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-06-28 | 🟢 Buy | BTC | $107,296.79 | $297.88 |  | weekly check: #3 by 120-day gain (+27%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-06-28 | 🟢 Buy | HYPE | $37.81 | $297.88 |  | weekly check: #1 by 120-day gain (+90%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-06-28 | 🟢 Buy | TRX | $0.2747 | $297.88 |  | weekly check: #4 by 120-day gain (+18%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-06-20 | 🔴 Sell | HYPE | $33.37 | $364.66 | $75.02 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-06-20 | 🔴 Sell | TRX | $0.2722 | $293.50 | $4.14 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-06-20 | 🔴 Sell | BTC | $103,297.99 | $283.80 | -$14.59 | BTC closed below its 50-day average (its uptrend broke) | backtest |
| 2025-06-20 | 🔴 Sell | BCH | $473.70 | $297.98 | $38.22 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-06-14 | 🔴 Sell | BNB | $645.61 | $255.47 | -$4.12 | no longer one of the top 5 at the weekly check | backtest |
| 2025-06-07 | 🟢 Buy | BCH | $409.40 | $258.56 |  | weekly check: #2 by 120-day gain (+28%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-06-07 | 🟢 Buy | BNB | $650.82 | $258.56 |  | weekly check: #4 by 120-day gain (+13%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-24 | 🟢 Buy | BTC | $107,761.91 | $297.26 |  | weekly check: #3 by 120-day gain (+3%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-17 | 🔴 Sell | BTC | $103,126.65 | $282.42 | -$6.89 | no longer one of the top 5 at the weekly check | backtest |
| 2025-05-17 | 🔴 Sell | LTC | $96.06 | $261.91 | -$27.31 | no longer one of the top 5 at the weekly check | backtest |
| 2025-05-17 | 🔴 Sell | XRP | $2.35 | $273.32 | -$15.95 | no longer one of the top 5 at the weekly check | backtest |
| 2025-05-10 | 🟢 Buy | BTC | $104,809.53 | $288.18 |  | weekly check: #2 by 120-day gain (+11%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-10 | 🟢 Buy | HYPE | $26.26 | $288.18 |  | weekly check: #1 by 120-day gain (+27%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-10 | 🟢 Buy | LTC | $105.27 | $288.18 |  | weekly check: #5 by 120-day gain (+1%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-10 | 🟢 Buy | TRX | $0.2662 | $288.18 |  | weekly check: #3 by 120-day gain (+9%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-10 | 🟢 Buy | XRP | $2.47 | $288.18 |  | weekly check: #4 by 120-day gain (+6%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-05-03 | 🔴 Sell | BTC | $95,856.42 | $290.94 | $1.41 | no longer one of the top 5 at the weekly check | backtest |
| 2025-04-30 | 🔴 Sell | XRP | $2.19 | $287.16 | -$2.35 | XRP closed below its 50-day average (its uptrend broke) | backtest |
| 2025-04-26 | 🟢 Buy | BTC | $94,628.00 | $288.37 |  | weekly check: #2 by 120-day gain (+0%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-04-26 | 🟢 Buy | XRP | $2.19 | $288.37 |  | weekly check: #1 by 120-day gain (+2%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-02-02 | 🔴 Sell | XRP | $2.58 | $299.82 | -$82.88 | XRP closed below its 50-day average (its uptrend broke) | backtest |
| 2025-02-02 | 🔴 Sell | BTC | $97,700.59 | $311.12 | -$25.02 | BTC closed below its 50-day average (its uptrend broke) | backtest |
| 2025-02-02 | 🔴 Sell | SOL | $203.51 | $263.72 | -$70.94 | SOL closed below its 50-day average (its uptrend broke) | backtest |
| 2025-02-02 | 🔴 Sell | LTC | $109.12 | $281.18 | -$25.33 | LTC closed below its 50-day average (its uptrend broke) | backtest |
| 2025-02-01 | 🟢 Buy | LTC | $118.04 | $305.39 |  | weekly check: #2 by 120-day gain (+82%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-28 | 🔴 Sell | LINK | $22.61 | $302.52 | -$33.59 | LINK closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-28 | 🔴 Sell | LTC | $109.92 | $295.88 | -$40.21 | LTC closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-25 | 🔴 Sell | XLM | $0.4172 | $323.06 | -$59.73 | XLM closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-25 | 🟢 Buy | BTC | $104,746.85 | $334.90 |  | weekly check: #5 by 120-day gain (+59%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-25 | 🟢 Buy | LINK | $24.93 | $334.90 |  | weekly check: #2 by 120-day gain (+97%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-25 | 🟢 Buy | LTC | $123.92 | $334.90 |  | weekly check: #3 by 120-day gain (+74%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-25 | 🟢 Buy | SOL | $256.41 | $333.61 |  | weekly check: #4 by 120-day gain (+63%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-20 | 🔴 Sell | SUI | $4.42 | $335.48 | -$47.36 | SUI closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-19 | 🔴 Sell | ADA | $0.9930 | $341.61 | -$41.25 | ADA closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-19 | 🔴 Sell | DOGE | $0.3584 | $343.54 | -$39.33 | DOGE closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-18 | 🟢 Buy | ADA | $1.10 | $381.50 |  | weekly check: #5 by 120-day gain (+214%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-18 | 🟢 Buy | DOGE | $0.3964 | $381.50 |  | weekly check: #3 by 120-day gain (+276%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-18 | 🟢 Buy | SUI | $5.00 | $381.50 |  | weekly check: #4 by 120-day gain (+240%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-18 | 🟢 Buy | XLM | $0.4907 | $381.50 |  | weekly check: #2 by 120-day gain (+411%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-18 | 🟢 Buy | XRP | $3.27 | $381.50 |  | weekly check: #1 by 120-day gain (+459%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-07 | 🔴 Sell | ADA | $0.9892 | $386.67 | -$35.09 | ADA closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-07 | 🔴 Sell | DOGE | $0.3480 | $368.89 | -$52.80 | DOGE closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-07 | 🔴 Sell | SUI | $4.79 | $378.57 | -$43.15 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-01-07 | 🔴 Sell | XLM | $0.4178 | $388.23 | -$33.53 | XLM closed below its 50-day average (its uptrend broke) | backtest |
| 2025-01-07 | 🔴 Sell | XRP | $2.27 | $392.78 | -$29.00 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2025-01-04 | 🟢 Buy | ADA | $1.07 | $420.21 |  | weekly check: #5 by 120-day gain (+240%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-04 | 🟢 Buy | DOGE | $0.3948 | $420.21 |  | weekly check: #4 by 120-day gain (+327%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-04 | 🟢 Buy | SUI | $5.29 | $420.21 |  | weekly check: #1 by 120-day gain (+532%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-04 | 🟢 Buy | XLM | $0.4504 | $420.21 |  | weekly check: #2 by 120-day gain (+412%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2025-01-04 | 🟢 Buy | XRP | $2.42 | $420.21 |  | weekly check: #3 by 120-day gain (+364%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-12-27 | 🔴 Sell | SUI | $4.08 | $394.45 | $192.87 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2024-12-27 | 🔴 Sell | XRP | $2.15 | $504.08 | $237.79 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2024-12-27 | 🔴 Sell | UNI | $13.35 | $430.12 | -$4.45 | bitcoin closed below its 50-day average, so the bot moved to cash | backtest |
| 2024-12-26 | 🔴 Sell | ADA | $0.8611 | $354.39 | $147.73 | ADA closed below its 50-day average (its uptrend broke) | backtest |
| 2024-12-26 | 🔴 Sell | XLM | $0.3547 | $426.44 | $158.33 | XLM closed below its 50-day average (its uptrend broke) | backtest |
| 2024-12-21 | 🟢 Buy | UNI | $13.38 | $432.85 |  | weekly check: #5 by 120-day gain (+91%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-12-19 | 🔴 Sell | DOGE | $0.3143 | $434.58 | $232.85 | DOGE closed below its 50-day average (its uptrend broke) | backtest |
| 2024-11-16 | 🔴 Sell | BTC | $90,586.92 | $263.90 | $62.84 | no longer one of the top 5 at the weekly check | backtest |
| 2024-11-16 | 🔴 Sell | SOL | $215.71 | $268.91 | $67.84 | no longer one of the top 5 at the weekly check | backtest |
| 2024-11-16 | 🟢 Buy | XLM | $0.2207 | $266.41 |  | weekly check: #3 by 120-day gain (+110%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-11-16 | 🟢 Buy | XRP | $1.12 | $264.27 |  | weekly check: #4 by 120-day gain (+96%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-11-09 | 🔴 Sell | TRX | $0.1621 | $206.06 | $5.24 | no longer one of the top 5 at the weekly check | backtest |
| 2024-11-09 | 🟢 Buy | ADA | $0.4967 | $205.24 |  | weekly check: #5 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-10-19 | 🟢 Buy | BTC | $68,378.00 | $200.00 |  | weekly check: #5 by 120-day gain (+7%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-10-19 | 🟢 Buy | DOGE | $0.1441 | $200.00 |  | weekly check: #4 by 120-day gain (+16%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-10-19 | 🟢 Buy | SOL | $159.79 | $200.00 |  | weekly check: #3 by 120-day gain (+19%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-10-19 | 🟢 Buy | SUI | $2.06 | $200.00 |  | weekly check: #1 by 120-day gain (+124%), in an uptrend, with bitcoin in an uptrend | backtest |
| 2024-10-19 | 🟢 Buy | TRX | $0.1567 | $200.00 |  | weekly check: #2 by 120-day gain (+32%), in an uptrend, with bitcoin in an uptrend | backtest |

</details>

[Rotation bot journal](crypto/journal-rotation.md)

## 🏦 Buy-and-hold bot

Bought equal thirds of BTC, ETH and SOL on day one and never sells.

### Holding now

| Coin | Value now | Paid | Profit / loss | Share of the bot |
|---|---|---|---|---|
| BTC | $395.67 | $333.33 | $62.34 (+18.7%) | 43% |
| ETH | $301.24 | $333.33 | -$32.10 (-9.6%) | 33% |
| SOL | $214.98 | $333.33 | -$118.35 (-35.5%) | 24% |
| Cash | $0.00 | | | 0% |

| Date | | Coin | Price | Amount | Profit / loss | Why | Type |
|---|---|---|---|---|---|---|---|
| 2024-10-19 | 🟢 Buy | BTC | $68,378.00 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good | backtest |
| 2024-10-19 | 🟢 Buy | ETH | $2,648.20 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good | backtest |
| 2024-10-19 | 🟢 Buy | SOL | $159.79 | $333.33 |  | day one: equal thirds of BTC, ETH and SOL, held for good | backtest |

[Buy-and-hold bot journal](crypto/journal-hold.md)

## Month by month

Each bot's value at the end of each month.

| Month end | Rotation bot | Buy-and-hold bot |
|---|---|---|
| 2026-10 | $1,627 | $912 |
| 2026-09 | $1,940 | $988 |
| 2026-08 | $1,544 | $905 |
| 2026-07 | $1,561 | $690 |
| 2026-06 | $1,517 | $635 |
| 2026-05 | $1,517 | $781 |
| 2026-04 | $1,459 | $826 |
| 2026-03 | $1,473 | $768 |
| 2026-02 | $1,473 | $747 |
| 2026-01 | $1,473 | $909 |
| 2025-12 | $1,496 | $1,057 |
| 2025-11 | $1,496 | $1,091 |
| 2025-10 | $1,496 | $1,404 |
| 2025-09 | $1,621 | $1,507 |
| 2025-08 | $1,765 | $1,493 |
| 2025-07 | $1,669 | $1,384 |
| 2025-06 | $1,512 | $1,153 |
| 2025-05 | $1,448 | $1,150 |
| 2025-04 | $1,437 | $989 |
| 2025-03 | $1,442 | $888 |
| 2025-02 | $1,442 | $998 |
| 2025-01 | $1,575 | $1,393 |
| 2024-12 | $2,101 | $1,266 |
| 2024-11 | $2,452 | $1,426 |
| 2024-10 | $1,043 | $1,008 |

## Files

- [Every trade, both bots (CSV)](crypto/trades.csv)
- [How these strategies were chosen](crypto/STRATEGIES.md)
