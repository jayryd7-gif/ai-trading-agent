# Agent dashboard

Last updated 2026-10-16 19:58 New York time. Everything here is written by software and AI agents. It can be wrong, so check anything you plan to act on.

## Agent status

| | Agent | What it does | Last ran | Runs |
|---|---|---|---|---|
| 🟢 | Market brief: nasdaq | Writes the brief before the New York session | 12 hours ago | weekdays about 7-8 AM New York time |
| 🟢 | Market brief: gold | Writes the brief before the Asia session | 24 hours ago | Sun-Thu evenings about 7-8 PM New York time |
| 🟢 | Scorer | Checks each lean against what price did | 2 hours ago | after each session ends |

🟢 ran recently  🟡 a bit late  🔴 check it  ⚪ never ran

## Latest lean for each market

| Market | Brief written | Lean | Confidence | Event risk | Price then | Full brief |
|---|---|---|---|---|---|---|
| nasdaq | 2026-10-16 08:28 | ◆ Neutral | Low | Medium | 30099.50 | [read it](reports/2026-10-16-nasdaq-brief.md) |
| gold | 2026-10-15 20:22 | ◆ Neutral | Low | High | 4175.00 | [read it](reports/2026-10-15-gold-brief.md) |

A lean is a probability-based view, not a prediction. ▲ Bullish  ▼ Bearish  ◆ Neutral

## Scorecard

- Briefs scored: **3** (Bullish or Bearish calls: 0)
- Right: 0, Wrong: 0, Session ended flat: 0
- Hit rate when the session was decisive: **n/a**
- For comparison, price went up in 33% of decisive sessions
- ⚠️ Only 0 directional calls so far. Treat the numbers as noise until there are at least 30.

By confidence:

| Confidence | Right | Wrong | Flat | Hit rate |
|---|---|---|---|---|
| High | 0 | 0 | 0 | n/a |
| Medium | 0 | 0 | 0 | n/a |
| Low | 0 | 0 | 0 | n/a |

[Full scorecard](reports/scorecard.md)

## Recent results

| Brief | Market | Lean | Confidence | Session moved | Result |
|---|---|---|---|---|---|
| 2026-10-16 | nasdaq | ◆ Neutral | Low | Down (-2.14%) | Moved |
| 2026-10-15 | gold | ◆ Neutral | Low | Up (0.81%) | Moved |
| 2026-10-15 | nasdaq | ◆ Neutral | Low | Down (-2.14%) | Moved |

## Your trade journal

Trades logged: **1**. [Open the journal](trade-journal.md)

## Still to build

| Agent | Purpose | Status |
|---|---|---|
| Post-session review agent | Reads your journal and the day's brief, writes what went well and what to improve | ⚪ not built yet |
| Stock research agent | Looks for promising companies early | ⚪ not built yet |
| Crypto research agent | Watches the crypto market for opportunities | ⚪ not built yet |
| Business research agent | Finds fast-growing products worth selling | ⚪ not built yet |
| Paper trading agent | Places practice trades through your broker, behind a risk gatekeeper | ⚪ not built yet |

## Links

- [All reports](reports/)
- [Trading rules](trading-rules.md)
- [Bias log](reports/bias-log.csv)
