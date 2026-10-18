# Crypto swing strategy (draft for review)

A buy-and-hold style strategy that steps aside when coins start to bleed and
buys back when the uptrend returns. It trades BTC, ETH, SOL, XRP and HYPE. It
does not use any of the futures rules.

Nothing here is trading yet. This is the proposal, backed by the tests in
`crypto/swing_backtest.py`. It is not financial advice, and past results do
not promise future ones.

## The rules

Checked once a day, at the daily close (8 PM New York in summer, 7 PM in winter).

1. **Own a coin only while it is in an uptrend:** its daily close is above
   its 50-day average.
2. **Alt coins also need bitcoin in an uptrend.** When bitcoin weakens, alts
   usually fall harder, so the agent sells them first.
3. **Get out before it bleeds:** when a coin closes below its 50-day average
   (or bitcoin does, for alts), sell it and sit in cash, earning nothing.
4. **Get back in when the trend returns,** usually at a lower price than the
   exit if the drop was big.
5. **Equal money in each coin,** split evenly across the coins.

## What the tests found

Equal money in BTC, ETH, SOL and XRP, from Sept 2020 to Oct 2026, after a
0.4% fee on every buy and sell:

| Version | $1 became | Worst fall along the way |
|---|---|---|
| Buy and hold | $13.87 | 91% |
| **This strategy (trend + bitcoin filter)** | **$45.58** | **58%** |

The same rules on five coins they were not built on (DOGE, LINK, AVAX, ADA
plus BTC): $34.39 versus $7.97 for buy and hold, worst fall 72% versus 90%.
So the rules are not just fitted to the coins above.

**What did NOT work: selling high and buying back lower.** Selling when price
looked stretched cut long-run growth from $45 to $8. In crypto, strong coins
often keep running, and selling early misses the biggest moves. Buying extra
on dips helped a little over six years, but not in the last two.

## Honest caveats

- **Most of the gain came from the 2020-2021 bull market.** From 2023 on, the
  strategy roughly matched buy and hold. Its main job since then has been
  cutting the falls, not beating the market.
- **The last 21 months were choppy for everything.** With HYPE included, the
  strategy grew $1 to $1.10 (trend only, without the bitcoin filter: $1.27)
  versus $1.15 for buy and hold, but its worst fall was 36% versus 56%.
- **Falls are still large.** Even with the exits, expect drops of 35-60% at
  times. Only use money you can leave alone through that.
- **It trades often around the trend line:** about 35 buys and sells per
  coin per year, many of them small losses when the trend flips back and
  forth. Fees matter: use an exchange with low fees.
- **HYPE only has 22 months of history,** so its results mean little yet.

## News (buying before the market reacts)

Trading ahead of news cannot be tested on past data, because there is no
record of what was known before each move. The plan: the crypto research
brief already flags government moves, whale buying, and coming events. In
paper trading, the agent will log what the brief said next to each trade, so
after a few months we can see whether news would have helped. It will not
act on news until that record exists.

## Next step

A crypto paper trader that runs these rules every day, keeps its own journal,
and shows on the dashboard, the same way the futures paper trader does.
