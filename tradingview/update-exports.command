#!/bin/bash
# Double-click this file after exporting the "List of trades" from your
# TradingView strategies (Strategy Tester > List of trades > download icon).
# It copies the newest export of EVERY strategy on MNQ1! and MGC1! from
# Downloads into the project (MAMBA NQ, OPENING RANGE, Session Breakout...),
# redraws the Nasdaq scripts chart, saves it all in a commit, and opens
# GitHub Desktop so you only have to click "Push origin".
cd "$(dirname "$0")/.." || exit 1
copied=0
for symbol in "MNQ1!" "MGC1!"; do
  found=0
  # newest file first; keep only the newest export of each strategy name
  seen=""
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    name=$(basename "$file")
    strategy="${name%%_CME*}"
    strategy="${strategy%%_COMEX*}"
    case "|$seen|" in *"|$strategy|"*) continue ;; esac
    seen="$seen|$strategy"
    cp "$file" tradingview/exports/
    echo "Copied: $name"
    copied=1
    found=1
  done < <(ls -t ~/Downloads/*"$symbol"*.csv 2>/dev/null)
  [ "$found" = 0 ] && echo "No $symbol export found in Downloads."
done
if [ "$copied" = 1 ]; then
  python3 agents/nasdaq_scripts_chart.py && echo "Redrew the Nasdaq scripts chart."
  git add tradingview/exports reports/charts/nasdaq-scripts.svg 2>/dev/null
  git commit -q -m "Update TradingView exports $(date +%F)" && echo "Saved in a commit."
  open -a "GitHub Desktop" .
  echo
  echo "Done. In GitHub Desktop, click Push origin. You can close this window."
else
  echo
  echo "Nothing to copy. Export the List of trades in TradingView first."
fi
