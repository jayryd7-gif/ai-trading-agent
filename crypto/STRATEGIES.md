# Crypto strategies that turned $1,000 into five figures (6-year test)

Tested in `crypto/strategy_lab.py` from Oct 18, 2020 to Oct 18, 2026: $1,000
start, daily decisions at the daily close, a 0.4% fee on every dollar traded,
no borrowing, no shorting. None of these use dip buying, selling high, or news.

The test coins are 18 large coins that already traded in late 2020,
**including ones that later collapsed** (EOS, BCH, ETC and others). Picking
only today's winners would make every strategy look better than it was.

This is research, not financial advice. Past results do not promise future
ones, and a 6-year test covers only about two big crypto cycles.

## Results

| Strategy | $1,000 became | Worst fall | 1st half (2020-23) | 2nd half (2023-26) |
|---|---|---|---|---|
| Buy and hold bitcoin (the benchmark) | $7,081 | 77% | 2.5x | 2.9x |
| Buy and hold all 18 coins | $8,165 | 86% | 3.8x | 2.2x |
| **1. Momentum rotation: top 5 by 120-day gain** | **$36,498** | 55% | 13.9x | 2.6x |
| **2. Trend + bitcoin filter, 100-day average** | **$21,630** | 54% | 9.4x | 2.3x |
| **3. Volatility-sized trend** (18 coins) | **$15,663** | **48%** | 6.9x | 2.3x |
| Rotation: top 3 by 90-day gain | $20,083 | 54% | 7.0x | 2.9x |
| Rotation: top 3 by 120-day gain | $23,889 | 57% | 9.1x | 2.6x |
| Rotation: top 3 by 180-day gain | $19,847 | 60% | 11.7x | 1.7x |
| 20/100-day average crossover | $14,879 | 69% | 6.2x | 2.4x |
| 20-day channel breakout | $9,202 | 46% | 5.3x | 1.8x |
| Dual momentum BTC/ETH | $5,126 | 69% | 3.1x | 1.7x |
| Rotation: top 1 coin only | $1,774 | 78% | 2.3x | 0.8x |
| Rotation by 30-day gain | $5,515 | 77% | 6.0x | 0.9x |

## The three I would consider

### 1. Momentum rotation (highest growth)
Once a week, rank the 18 coins by how much they gained over the last 120
days. Hold the top 5, in equal amounts, but only coins above their 50-day
average, and only while bitcoin is above its 50-day average too. Between the
weekly checks, sell any coin whose uptrend breaks. When bitcoin's trend
breaks, go fully to cash.

Why it might work: coins that have been strongest for several months tend
to keep leading for a while, and the trend filters move to cash in crashes.
What makes it believable: every lookback from 90 to 180 days made five
figures and grew in both halves. Short lookbacks (30 days) and holding just
one coin did badly, so do not shorten or concentrate it.

### 2. Trend + bitcoin filter (simplest)
Own each of the 18 coins while it is above its 100-day average, and own alt
coins only while bitcoin is above its 100-day average too. Otherwise cash.
Fewer trades than the 50-day version, similar results.

### 3. Volatility-sized trend (smoothest)
Same as 2 with a 50-day average, but hold less of a coin when it is swinging
wildly, so a calm coin gets a bigger share than a wild one. Lowest worst
fall of the five-figure group (48%).

## What did not work
- Holding only the single strongest coin: too concentrated, $1,774.
- Short lookbacks (30 days): chases noise, $5,515.
- Switching between only BTC and ETH: $5,126.
- The futures-style breakout on 5-minute candles: lost money after fees.
- Selling high and buying back lower: missed the big runs.

## Honest caveats
- **Expect falls of about 50% at some point**, even with every filter.
- **Most of the growth came in the first half** (the 2020-21 bull run).
  Since late 2023 the best ones grew about 2.3-2.9x, similar to holding
  bitcoin, but with smaller falls.
- **The best result of many tests is always flattered.** The rotation
  family is the most trustworthy here because many settings worked, not
  just one.
- **Fees:** results assume 0.4% per trade. Use a low-fee exchange; higher
  fees eat most of the edge from frequent trades.
- HYPE has only 22 months of history, so it is not in these tests. It can
  join the rotation list once it has more.

## Next step
Pick one (or run two side by side), and I will build a crypto paper trader
for it, with its own journal and dashboard section, the same way the
futures paper trader works.
