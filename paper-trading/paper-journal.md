# Paper trading journal

Written automatically by paper_trader.py as each paper trade closes. Nothing here is a real trade.

---

### ✅ 2026-10-22 | Gold (MGC) | Short | $415
- **Session start (New York):** 2026-10-21 20:00
- **Why:** two 5-minute candles closed beyond the key low (4139.1)
- **Entry:** Sold short **5 contracts** at **4137.2** at **20:15** (sell plan 1/2/2)
- **Stop:** 4143.1

| Time | What | Contracts | Price | Profit |
|---|---|---|---|---|
| 20:35 | Target 1 | 1 | 4131.2 | $60 |
| 21:25 | Target 2 | 2 | 4125.2 | $240 |
| 21:30 | Stop | 2 | 4131.2 | $120 |

- **Exit:** last contract out at **21:30**, average 4128.8
- **Result:** $420 before fees, **$415 after fees**
- **What could have gone better:**
  - Moving the stop to Target 1 after Target 2 locked in the profit; price never reached Target 3 afterwards.
  - Biggest move against you while in the trade: 0.80 points ($40 on paper). Best move for you: 13.50 points.

![Chart of this trade](charts/2026-10-21-gold.svg)

[Open Gold (MGC) on TradingView](https://www.tradingview.com/chart/?symbol=COMEX_MINI%3AMGC1%21&interval=5) (add tradingview/breakout_strategy.pine to see this trade marked)

---

### ❌ 2026-10-21 | Nasdaq (MNQ) | Short | -$252
- **Session start (New York):** 2026-10-21 09:30
- **Why:** two 5-minute candles closed beyond the key low (29832.75)
- **Entry:** Sold short **5 contracts** at **29818.5** at **10:15** (sell plan 1/2/2)
- **Stop:** 29843.25

| Time | What | Contracts | Price | Profit |
|---|---|---|---|---|
| 10:20 | Stop | 5 | 29843.25 | -$248 |

- **Exit:** last contract out at **10:20**, average 29843.25
- **Result:** -$248 before fees, **-$252 after fees**
- **What could have gone better:**
  - Price never reached Target 1: the best it did was +25.75 points, and Target 1 needed 30.
  - The breakout failed and price kept going the other way, so the stop did its job and kept the loss small.
  - Biggest move against you while in the trade: 41.75 points ($418 on paper). Best move for you: 25.75 points.

![Chart of this trade](charts/2026-10-21-nasdaq.svg)

[Open Nasdaq (MNQ) on TradingView](https://www.tradingview.com/chart/?symbol=CME_MINI%3AMNQ1%21&interval=5) (add tradingview/breakout_strategy.pine to see this trade marked)

---

### ✅ 2026-10-20 | Nasdaq (MNQ) | Long | $655
- **Session start (New York):** 2026-10-20 09:30
- **Why:** two 5-minute candles closed beyond the key high (29636.0)
- **Entry:** Bought **5 contracts** at **29717.75** at **10:05** (sell plan 1/2/2)
- **Stop:** 29604.0

| Time | What | Contracts | Price | Profit |
|---|---|---|---|---|
| 10:15 | Target 1 | 1 | 29747.75 | $60 |
| 10:15 | Target 2 | 2 | 29777.75 | $240 |
| 10:25 | Target 3 | 2 | 29807.75 | $360 |

- **Exit:** last contract out at **10:25**, average 29783.75
- **Result:** $660 before fees, **$655 after fees**
- **What could have gone better:**
  - Price kept going 95.75 points past Target 3 (by 10:30). Letting the last 2 contract(s) run with a trailing stop could have made up to $383 more.
  - Biggest move against you while in the trade: 25.75 points ($258 on paper). Best move for you: 165.25 points.

![Chart of this trade](charts/2026-10-20-nasdaq.svg)

[Open Nasdaq (MNQ) on TradingView](https://www.tradingview.com/chart/?symbol=CME_MINI%3AMNQ1%21&interval=5) (add tradingview/breakout_strategy.pine to see this trade marked)

---

### ✅ 2026-10-20 | Gold (MGC) | Short | $415
- **Session start (New York):** 2026-10-19 20:00
- **Why:** two 5-minute candles closed beyond the key low (4150.7)
- **Entry:** Sold short **5 contracts** at **4150.6** at **20:55** (sell plan 1/2/2)
- **Stop:** 4152.4

| Time | What | Contracts | Price | Profit |
|---|---|---|---|---|
| 21:00 | Target 1 | 1 | 4144.6 | $60 |
| 21:15 | Target 2 | 2 | 4138.6 | $240 |
| 21:40 | Stop | 2 | 4144.6 | $120 |

- **Exit:** last contract out at **21:40**, average 4142.2
- **Result:** $420 before fees, **$415 after fees**
- **What could have gone better:**
  - Moving the stop to Target 1 after Target 2 locked in the profit; price never reached Target 3 afterwards.
  - Biggest move against you while in the trade: -0.10 points (-$5 on paper). Best move for you: 16.10 points.

![Chart of this trade](charts/2026-10-19-gold.svg)

[Open Gold (MGC) on TradingView](https://www.tradingview.com/chart/?symbol=COMEX_MINI%3AMGC1%21&interval=5) (add tradingview/breakout_strategy.pine to see this trade marked)

---

### ✅ 2026-10-19 | Nasdaq (MNQ) | Long | $357
- **Session start (New York):** 2026-10-19 09:30
- **Why:** two 5-minute candles closed beyond the key high (29794.25)
- **Entry:** Bought **3 contracts** at **29841.25** at **10:15** (sell plan 1/1/1)
- **Stop:** 29694.0
- **Small size:** less than $1,500 was left before the $4,000 max drawdown, so it traded 1 contract per target.

| Time | What | Contracts | Price | Profit |
|---|---|---|---|---|
| 11:00 | Target 1 | 1 | 29871.25 | $60 |
| 11:15 | Target 2 | 1 | 29901.25 | $120 |
| 11:20 | Target 3 | 1 | 29931.25 | $180 |

- **Exit:** last contract out at **11:20**, average 29901.25
- **Result:** $360 before fees, **$357 after fees**
- **What could have gone better:**
  - Price kept going 52.25 points past Target 3 (by 11:35). Letting the last 1 contract(s) run with a trailing stop could have made up to $104 more.
  - Biggest move against you while in the trade: 81.00 points ($486 on paper). Best move for you: 104.00 points.

![Chart of this trade](charts/2026-10-19-nasdaq.svg)

[Open Nasdaq (MNQ) on TradingView](https://www.tradingview.com/chart/?symbol=CME_MINI%3AMNQ1%21&interval=5) (add tradingview/breakout_strategy.pine to see this trade marked)

---

## Total

- **Total profit / loss after fees:** **$1,590** over 5 trades
- **Winners:** 4 (80%), **losers:** 1
- **Before fees:** $1,612, fees paid: $23
- **Nasdaq (MNQ):** $760 over 3 trades
- **Gold (MGC):** $830 over 2 trades
