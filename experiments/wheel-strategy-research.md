# Options Wheel Strategy: Research Batch (2026-11-14)

This is research only. It is not financial advice, and none of these rules are tested on our data yet.
Next step: backtest it, then paper trade it, before any real money goes in (see "Data decides").

## The wheel in one line
1. Sell a cash-secured put on a stock you'd be fine owning. Keep the premium.
2. If you get assigned, you own 100 shares. Sell covered calls above your cost.
3. If the shares get called away, go back to step 1.

## What the experts and studies agree on

| Rule | What the sources say | Where it comes from |
|---|---|---|
| Days to expiration | Sell about **30-45 days out**. 45 DTE had the best profit per day. | tastylive SPY studies since 2005, Spintwig backtests |
| Take profit | **Close at 50% of max profit** and sell a new one | tastylive "manage at 50%" research |
| Time exit | Or close at **21 days left**, whichever comes first. This avoids the fast swings near expiry. | tastylive 2019/2020 studies |
| Put strike (delta) | **0.20-0.30 delta** (roughly a 70-80% chance it expires worthless) | Option Alpha, most wheel guides |
| Call strike | **0.20-0.30 delta, at or above your cost basis** so you never lock in a loss | Wheel guides |
| Stock choice | Only **solid stocks you'd hold anyway**, trending up or flat with support. No meme stocks. | Markus Heitkoetter (Rockwell Trading), Option Alpha |
| Earnings | **Don't hold a short option through earnings** | Heitkoetter |
| IV rank | Sell when **IV rank is about 30-50**. Above 70 usually means a big event is coming. | Practitioner guides |
| Liquidity | Tight bid/ask spreads and **1,000+ open interest** at your strike | Practitioner guides |
| Size | Each put needs strike x 100 in cash (a $50 strike ties up $5,000) | How the trade works |

## About "quick profits": the honest results
- **Weeklies are not better.** tastylive and Luckbox studies found monthly (about 45 DTE) short options had a better risk/reward than weeklies. Weeklies pay faster but swing harder and need constant watching.
- **Win rates look great, losses are bigger.** 30-delta SPY puts won about 70% of the time in one 2020-2024 backtest, but the average loser was bigger than the average winner.
- **Drawdowns are real.** Expect roughly **-20% to -30%** in selloffs, because assignments bunch up when the market falls.
- **Long run vs just buying the index.** The CBOE PutWrite index (PUT) roughly matched the S&P 500 from 1988 to 2007 with less volatility. In strong bull years, like 2023-2024, it **trailed** the S&P. The covered call index (BXM) beat the S&P in only 4 of 18 years from 2003 to 2020.
- **Where the money comes from.** One SPY wheel backtest found almost all of the return came from **owning the stock**. The option premium added very little over the long run.

Bottom line: the wheel is a steady-income strategy. It is not a fast-money strategy. The best-tested version is 45 DTE, about 0.30 delta, take 50% or exit at 21 DTE, on quality liquid names.

## Draft rule set to backtest (nothing built yet)
1. Universe: liquid, optionable stocks or ETFs with no earnings before expiry and IV rank between 30 and 50.
2. Entry: sell a 0.25-0.30 delta put, 30-45 DTE.
3. Exit: buy it back at 50% profit, or at 21 DTE, whichever comes first.
4. If assigned: sell a 0.30 delta call, 30-45 DTE, strike at or above cost basis. Same 50% / 21 DTE exits.
5. Risk: no more than X% of the account in one name, and stop opening new puts if the account is down Y% (to be set from the backtest).
6. Compare against just buying and holding the same stock. If it doesn't beat that on risk-adjusted terms, we don't run it.

## 90-day backtest: $2,500 CAD (2026-08-15 to 2026-11-13)
Run it again with `python3 experiments/wheel_backtest.py`. The option prices are **estimates** from a formula (Black-Scholes), because free data has no real past option prices.
$2,500 CAD is about $1,752 USD, so the highest strike that fits is about $17.50. That's one contract on one stock at a time.

| Stock | Wheel (45 DTE) | Wheel (weekly) | Just holding the stock |
|---|---|---|---|
| F | -6.3% | -8.7% | -14.2% |
| VALE | -14.6% | -17.7% | -18.3% |
| ITUB | -3.9% | -5.6% | +2.4% |
| NU | +2.6% | -4.3% | -10.2% |
| AAL | +2.5% | +4.2% | -8.7% |
| RIVN | -9.8% | -10.7% | -18.0% |
| SOFI | -6.7% | +1.7% | -15.7% |
| SNAP | +0.4% | +2.5% | +1.5% |
| RIG | -0.8% | +0.4% | -5.6% |
| **Average** | **-4.1%** | **-4.2%** | **-9.6%** |

What it shows: these cheap stocks mostly fell over the 90 days. The wheel lost about **half as much** as just holding them, but it still lost money on average (about -$100 CAD). Most early closes were small wins of $10-60. The losses came from getting stuck with shares that kept falling.

## Backtest at $10K CAD, up to 4 stocks (run 2026-11-14)
$10,000 CAD is about $7,008 USD. Each stock may tie up at most 25% ($1,752), so a strike can be at most about $17.50.

| Window | A: no filters (LIVE) | B: trend filter | C: trend + IV cap | Holding the same stocks |
|---|---|---|---|---|
| 90 days | **-0.2%** (-20 CAD), worst drop 5.5% | +0.4%, worst drop 5.9% | -4.9% | -10.6% |
| 60 days | **-0.8%** (-75 CAD), worst drop 5.4% | -5.1% | -4.9% | -9.6% |
| 30 days | **-2.0%** (-197 CAD), worst drop 5.2% | -2.9% | -3.2% | -4.8% |

Spreading over 4 stocks cut the worst drop to about 5% (one stock alone: 10-18%).
Neither filter helped in this down market, so the paper trader starts with version A. Earnings are still skipped.

## Paper trader (live from 2026-11-16)
- `agents/wheel_trader.py` runs every weekday at 2:37 PM New York on GitHub, using real Yahoo option prices. Settings are in `agents/wheel_rules.py`.
- Every move goes to your phone. The account is in `paper-trading/wheel/summary.md` and every move in `journal.md`.
- Plan: paper for a few months, then $2,500 CAD real money placed by hand with the phone alerts, then maybe automatic later.

## Things to know for our setup
- **Tradeify can't do this.** It's a futures prop account. The wheel needs a normal brokerage with options approval and enough cash to secure the puts.
- **The backtest needs historical option-chain data.** Free sources are thin. Under the zero-cost rule, the cheapest path is to paper trade it live for about 15 cycles and track the results.

## Sources
- tastylive: [45 DTE / duration studies](https://tastylive.com/shows/market-measures/episodes/optimal-dte-for-daily-income-01-20-2017), [why manage at 50%](https://tastylive.com/shows/options-jive/episodes/why-manage-at-50-not-25-for-short-strangles-09-13-2016), [managing at 21 days](https://www.tastylive.com/shows/best-practices/episodes/managing-21-days-early-02-25-2020), [short put management](https://www.tastylive.com/shows/market-measures/episodes/short-put-management-performance-09-12-2018)
- [Luckbox: monthly vs weekly short options](https://luckboxmagazine.com/?p=22368)
- [Option Alpha: wheel strategy](https://optionalpha.com/blog/wheel-strategy)
- Markus Heitkoetter: [book summary](https://www.shortform.com/summary/the-wheel-options-trading-strategy-summary-markus-heitkoetter), [podcast on exits](https://rockwelltrading.transistor.fm/episodes/ep-217-wheel-options-strategy-when-to-exit-trades)
- Spintwig / Early Retirement Now: [option writing part 5](https://earlyretirementnow.com/2020/06/17/passive-income-through-option-writing-part-5), [part 9 backtest](https://earlyretirementnow.com/2021/11/10/passive-income-through-option-writing-part-9-2016-2021-backtest-guest-post-by-spintwig/amp/), [summary](https://the7circles.uk/?p=34272)
- CBOE indexes: [Callan BXM study](https://cdn.cboe.com/resources/education/research_publications/Callan_CBOE.pdf), [First Trust on BXM](https://www.ftportfolios.com/Blogs/MarketBlog/2021/5/18/this-covered-call-index-tends-to-outperform-the-sp-500-when-stock-returns-are-modest-or-negative), [Dividend.com on BXM/PUT](https://www.dividend.com/options-and-income-channel/is-options-upside-becoming-capped/)
- Backtests: [Apexvol cash-secured put](https://apexvol.com/strategies/cash-secured-put/backtest), [Lambda Finance SPY wheel](https://www.lambdafin.com/articles/wheel-strategy-spy-backtest), [FlashAlpha put spreads](https://flashalpha.com/articles/spy-put-credit-spread-active-backtest-mm-fills-vrp-signal-drawdown-breaker)
- Screening tips: [QuantWheel expiration selection](https://quantwheel.com/learn/options-expiration-selection), [wheel mistakes](https://wheelstrategy.substack.com/p/wheel-strategy-mistakes)

## Options With Ryan's wheel (checked 2026-11-14)
His rules, as summarized by a third-party write-up of his CRDO wheel video ([CandleChasers](https://candlechasers.com/wheel-options-premium-assignment-risk/)). They are not verified from the video itself.
- **Puts:** about 0.25-0.30 delta, 25-35 days out.
- **Calls:** about 0.30 delta, 15-25 days out, at or above the cost basis.
- **Take profit:** close at about 80% profit, or roll.
- **Stock filter:** up for about 1.5 years, earnings beats, P/E under 100, and at least about 2.5% premium per 30 days.
- **Sizing:** at most about 10% of the account per company, with about 20-25% kept in cash.
- **His stocks** (CRDO, NVDA, HOOD, BE, PLTR, AMD) cost $78-$534 a share. One put on the cheapest (HOOD) ties up about $7,800 USD, which is more than the whole $10K CAD account.

Backtest (`PYTHONPATH=agents python3 experiments/wheel_backtest.py --ryan`):

| Window | Ours, our stocks, $10K CAD | Ryan's rules, our stocks, $10K CAD | Ryan's rules, his stocks, $200K USD | Holding his stocks |
|---|---|---|---|---|
| 90 days | -0.2% (worst drop 5.5%) | +0.2% (worst drop 1.6%, only 3 trades) | +1.2% (worst drop 5.8%) | -19.1% |
| 60 days | -0.8% | +0.2% | -2.1% | -14.5% |
| 30 days | -2.0% | 0.0% | -2.3% | -19.8% |

With $10K CAD, Ryan's rules on his own stocks made **0 trades**, because nothing fits.

### Ryan-style paper account (from 2026-11-16)
At the user's request, a second paper account runs next to ours so the two can be compared by %:
- **Money:** pretend $200,000 USD, on his stocks (CRDO, NVDA, HOOD, BE, PLTR, AMD).
- **His rules** (`ryan` in `agents/wheel_rules.py`): puts at 0.28 delta, 25-35 days; calls 15-25 days, at or above cost; take profit at 80%; uptrend over 1.5 years; P/E between 0 and 100; at least 2.5% premium per 30 days; at most 10% per company (several contracts); keep 20% in cash.
- **Earnings:** his earnings rule isn't stated, so this account does not skip earnings.
- **Files and alerts:** results in `paper-trading/wheel-ryan/`. Its phone alerts are low priority.
- **First test run (Nov 14):** it sold 2 HOOD $72 puts and 1 NVDA $150 put. BE and PLTR were skipped for P/E above 100, and AMD was too big for a 10% slot.

## 1-year backtest on volatile, heavily traded stocks (2025-11-13 to 2026-11-13)
Run: `PYTHONPATH=agents:experiments python3 experiments/wheel_year_backtest.py`. Option prices are estimates. Stocks were picked using only data from before the year started: the 10 most-traded with annual volatility of 50%+ (cheap) or 45%+ (big). Leveraged ETFs were left out.

| | Ours ($10K CAD) | Ryan-style ($200K USD) |
|---|---|---|
| Stocks | OPEN, MARA, SOUN, BBAI, SNAP, CIFR, RIVN, JOBY, QS, RIOT | PLTR, HOOD, INTC, BABA, RGTI, OKLO, SOFI, IONQ, MRVL, HIMS |
| Year result | **+9.9% (+$989 CAD)** | **+4.1% (+$8,253 USD)** |
| Best point in the year | +24.7% (Jun 1) | +18.6% (Sep 24) |
| Worst drop from a high | 13.5% | 15.7% |
| Premium collected | $3,736 CAD | $93,973 USD |
| Options closed at a profit / loss | 82 / 9 | 147 / 0 |
| Times assigned shares | 4 | 15 |
| Up months | 9 of 13 | 7 of 13 |
| Best / worst month | +6.5% / -5.0% | +9.7% / -7.8% |
| Holding at the end | shares of OPEN, BBAI, JOBY, QS | shares of 7 stocks, 1 put |
| Just holding the same 10 stocks | **-50.3%** | **-19.9%** |
| Just holding SPY | +13.5% | +13.5% |

What it shows:
- Both wheels beat holding the same volatile stocks by a lot.
- Neither beat simply holding SPY.
- Both gave back gains after the summer, because they were left holding shares of falling stocks.
- Ryan's "147 wins, 0 losses" hides the losses: they sit in the assigned shares, not in closed trades.
- Ryan's P/E filter couldn't be tested (no past P/E data).

## Can $10K CAD make $500-2,000 CAD a month? (tested 2026-11-15)
That goal means 60-240% a year. Run: `PYTHONPATH=agents:experiments python3 experiments/income_strategies.py`. All option prices are estimated.

Average CAD per month, with the worst drop from a high in brackets:

| Approach | Last 1 year | Last 3 years | Last 5 years |
|---|---|---|---|
| Wheel, current rules | $76 (13%) | $81 (16%) | - |
| Wheel, 0.40 delta, 30 days | -$189 (29%) | $161 (12%) | - |
| Weekly wheel | -$81 (22%) | $154 (19%) | - |
| Put spreads SPY/QQQ/IWM, 45 days, 10% risk | $49 (6%) | $393 (36%) | - |
| Weekly put spreads, 20% risk | -$341 (**87%**) | $2,394 (**95%**) | - |
| Put spreads on volatile big stocks | -$554 (**76%**) | - | - |
| **Iron condors SPY/QQQ, 30 days, 0.20 delta, 15% risk, 2x stop** | **$244 (16%)** | **$187 (26%)** | **$99 (30%)** |
| Iron condors, same but 25% risk | $291 (31%) | $1,317 (45%) | $128 (**56%**) |
| Put spreads 42 days, 15% risk, 45% max | $333 (29%) | $770 (56%) | $174 (**59%**) |

What it shows:
- **Hitting $500+ a month needed so much risk that the account could drop 45-95%.** Those approaches only "worked" in some years.
- **Sustainable approaches made about $75-250 CAD a month**, with 15-35% drops along the way.
- **Results swing a lot with small setting changes.** Iron condors at 0.16 delta lost money where 0.20 delta made money, so these are fragile. Paper trading should come before trusting any of them.
- **Wealthsimple:** spreads and iron condors need multi-leg orders. One review says Wealthsimple doesn't support them, so check the app first.

## Iron condor income paper account (live from 2026-11-16)
`agents/condor_trader.py` runs in the same daily job as the wheel accounts. It's a separate $10K CAD cash-flow test.
- **What it trades:** SPY and QQQ iron condors, one each, about 30 days out. Short strikes at 0.20 delta, wings about 2% wide (about $14-15).
- **Exits:** close at 50% profit, at 14 days left, or at a 2x stop.
- **Risk:** about 15% of the account per condor. A single contract may risk up to 18%, because one SPY condor risks about 16% of $10K CAD. All open condors together risk at most 36%.
- **Tested alternatives:** $5-wide wings lost money over 1, 3 and 5 years, and 1.5%-wide wings made much less, so the wings stay about 2%.
- **First test run (Nov 15):** SPY 706/721 + 782/797 for a $3.67 credit, and QQQ 620/635 + 723/737 for $4.16. About $780 of max gain for about $2,220 of max loss.
- **Files:** results in `paper-trading/condor/` (monthly cash-flow table included). Phone alerts are titled "Condor: …".
